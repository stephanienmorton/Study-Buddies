from .models import VSBUser, Course, GroupUser, StudyGroup, MAX_TIME_BYTES
from .util import convert_comfort_string_to_float_array, convert_available_times_json_to_boolarray

from operator import attrgetter
from enum import Enum

import numpy

#BUG:  Make sure users can't join groups they are a part of.

class Scoring:
    SELECTION_THRESHOLD = 25
    DISPLAY_LIMIT = 10
    FRACTION_AVAILABILITY = 0.65
    FRACTION_HELPING = 1 - FRACTION_AVAILABILITY #May want to make this function asymetric

    class ResultEnum(Enum):
        GOOD_GROUP_FOUND = 0
        NO_GROUPS_FOUND = 1
        POOR_GROUPS_FOUND = 2

    class BuildingScoreConsts:
        k = 0.38
        a = k - 2*numpy.sqrt(1 - k) - 2
        b = -3*a - k
        c = 2*(a + k)
    @staticmethod
    def building_score(users, limit):
        """
        Quadratic function following the following rules:
        y(1)=k
        y(-b/2a)=1
        y(limit)=0
        """
        x = (users + limit - 2)/(limit - 1) #Scales down to the precomputed function
        return Scoring.BuildingScoreConsts.a*x**2 + Scoring.BuildingScoreConsts.b*x + Scoring.BuildingScoreConsts.c

    class ComfortConsts:
        n = 5 #Score goes from 1 to n.  Get this from somewhere, but has to be less than 
        n2 = n**2 #Saves time in the function call
    @staticmethod
    def help_score(score1, score2):
        return (score1*score2 - 1)/(Scoring.ComfortConsts.n2 - 1)

class GroupScore:
    __group = None
    __building_factor = 0
    __availability_factor = 0
    __helping_factor = 0
    __precomputed_score = 0 #ranges b/t 0 and 100

    def get_score(self):
        return self.__precomputed_score

    def get_group(self):
        return self.__group

    def get_helping_factor(self):
        return self.__helping_factor

    def get_availability_factor(self):
        return self.__availability_factor

    def get_building_factor(self):
        return self.__building_factor

    def __lt__(self, other):
        return self.__precomputed_score < other.__precomputed_score

    def __init__(self, vsbuser, group, course_comfort_array):
        self.__group = group
        #Build limit
        build_limit = group.course.build_limit
        if group.is_building():
            self.__building_factor = Scoring.building_score(group.max_users_seen, build_limit)
        else:
            self.__building_factor = 0

        #Covert array if needed
        if type(course_comfort_array) == str:
            course_comfort_array = convert_comfort_string_to_float_array(course_comfort_array)

        #Timezone
        bucket_length = MAX_TIME_BYTES*8
        timezone_buckets = [0 for _ in range(bucket_length)]
        incoming_availability = convert_available_times_json_to_boolarray(vsbuser.available_times)
        num_users = len(group.groupuser_set.all())
        for user in group.groupuser_set.all():
            availability = convert_available_times_json_to_boolarray(user.course_user.vsb_user.available_times)
            if len(availability) == len(incoming_availability): #prevent errors
                for i in range(bucket_length):
                    timezone_buckets[i] += incoming_availability[i] and availability[i]
        
        try:
            self.__availability_factor = sum(timezone_buckets)/num_users/sum(incoming_availability)
        except ZeroDivisionError:
            self.__availability_factor = 0

        #Helping
        for user in group.groupuser_set.all():
            if not user.course_user.dirty_comfort:
                comfort = convert_comfort_string_to_float_array(user.course_user.course_comfort)
                for i in range(len(course_comfort_array)):
                    self.__helping_factor += Scoring.help_score(course_comfort_array[i], comfort[i])
        try:
            self.__helping_factor /= num_users*len(course_comfort_array)
        except ZeroDivisionError:
            self.__helping_factor = 0

        self.__precomputed_score = 100*self.__building_factor*(
            Scoring.FRACTION_AVAILABILITY*self.__availability_factor +
            Scoring.FRACTION_HELPING*self.__helping_factor
            )

def generate_matching_groups(vsbuser, course, course_comfort_array):
    """
    Creates a list of best matching groups in a descending order.
    Returns a list and an enumeration of the result.  It does not handle
    """
    groups = StudyGroup.objects.filter(course_id=course.id)
    all_groups = [group for group in groups]
    groups = []
    try: #a user may not exist
        c_user = vsbuser.courseuser_set.get(course=course)
        if c_user: #user may have other groups; filter
            user_groups =[guser.study_group for guser in c_user.groupuser_set.all()]
            for i in range(len(all_groups)):
                if not (all_groups[i] in user_groups):
                    groups.append(all_groups[i])
    except:
        groups = all_groups
        
    result = None
    group_scoring = []

    #Result Initialization
    if len(groups) > 0:
        for group in groups:
            score = GroupScore(vsbuser, group, course_comfort_array)
            if score.get_score() > 0:
                group_scoring.append(score)
        
        #Sort groups by score
        group_scoring.sort(reverse=True) #Sorted highest first

    if len(group_scoring) > 0:
        if group_scoring[0].get_score() < Scoring.SELECTION_THRESHOLD:
            result = Scoring.ResultEnum.POOR_GROUPS_FOUND
        else:
            result = Scoring.ResultEnum.GOOD_GROUP_FOUND
    else:
        result = Scoring.ResultEnum.NO_GROUPS_FOUND
    
    return (group_scoring, result)


def match_user(vsbuser, course, course_comfort_array):
    """
    A function to determine the best group or a list of poor groups for a user joining a course, if a group exists at all.
    The function does NOT modify the data layer.
    """
    (group_scoring, result) = generate_matching_groups(vsbuser, course, course_comfort_array)

    #Result Processing
    extra_data = None
    if result == Scoring.ResultEnum.GOOD_GROUP_FOUND:
        # Stores the best-scoring group in extra_data.
        extra_data = group_scoring[0]
    elif result == Scoring.ResultEnum.POOR_GROUPS_FOUND:
        # Stores a number of top-scoring groups for the user to select from.
        extra_data = group_scoring[0:Scoring.DISPLAY_LIMIT]

    return (result, extra_data)