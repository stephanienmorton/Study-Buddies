from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django import forms
import groupy
from groupy import Client
import numpy
import array
import json

BITS_PER_HOUR = 1 # Must be an integer
DAY_BYTES = 3*BITS_PER_HOUR
MAX_TIME_BYTES = 7*DAY_BYTES


class Eventful(models.Model):
    pass


# Group Models
class Institution(models.Model):
    name = models.CharField(max_length=80)
    def __str__(self):
        return self.name

class Course(models.Model):
    institution = models.ForeignKey("Institution", on_delete=models.PROTECT) #Don't let an accidential institution deletion remove all the courses
    name = models.CharField(max_length=80)
    build_limit = models.IntegerField(default=4)
    topics = models.CharField(default="", max_length=1000, blank=False) #A new line-delimited string for the topics in a course.

    from enum import Enum

    class __TopicOperation(Enum):
        ADDING = 0
        REMOVING = 1

    def __parse_topics(self):
        rarr = self.topics.split(';')
        if rarr[-1] == '': #remove any empty strings at the end
            del rarr[-1]
        return rarr

    def __encode_topics(self, topics): #Note that the topics are saved to the model with this call.
        out_str = ""
        for item in topics: #topics in the list
            out_str += item + ';'
        
        self.topics = out_str
        self.save()

    def __update_observers(self, operation, data=None):
        """
        Updates the group models of all users.
        Certain operations have additional data to provide, encoded in the 'data' parameter.
        """
        courseuser_set = self.courseuser_set.all()
        for cuser in courseuser_set:
            if operation == Course.__TopicOperation.ADDING:
                cuser.dirty_comfort = True
            elif operation == Course.__TopicOperation.REMOVING:
                responses = cuser.course_comfort
                prestr = responses[0:data]
                poststr = responses[(data+1):len(responses)]
                cuser.course_comfort = prestr + poststr
            cuser.save()



    def get_topics(self):
        return self.__parse_topics()

    def add_topic(self, topic):
        """
        Adds a topic and returns true.  Otherwise, returns false.
        """
        if topic == '':
            return False
        topics = self.__parse_topics()
        if topic in topics:
            return False
        topics.append(topic)
        self.__encode_topics(topics)
        self.__update_observers(Course.__TopicOperation.ADDING)
        return True
    
    def remove_topic(self, topic):
        topics = self.__parse_topics()
        if topic in topics:
            index = topics.index(topic)
            topics.remove(topic)
            self.__encode_topics(topics)
            self.__update_observers(Course.__TopicOperation.REMOVING, index)

    def rename_topic(self, old_name, new_name):
        """
        Renames a topic and returns True.  Otherwise, returns False.
        Keeps user answers intact.
        """
        topics = self.__parse_topics()
        if old_name in topics:
            index = topics.index(old_name)
            topics[index] = new_name
            self.__encode_topics(topics)

    def __str__(self):
        return self.name

class StudyGroup(Eventful):
    course = models.ForeignKey("Course", on_delete=models.PROTECT)
    default_name = models.CharField(max_length=50, blank=False)
    max_users_seen = models.IntegerField(default=0) #When this value is equal to or greater than the build_limit of the course, the system does not automatically add users.
    groupme_link = models.CharField(max_length=150, blank=True, null=True)
    # token = models.CharField(max_length=50, blank=True, null=True)
    #BUG: max_users_seen will increment is someone reinvites someone who left.

    def add_user(self, vsbuser):
        """
        Instantiate and initialize a new group user.
        """
        cuser = vsbuser.courseuser_set.filter(course=self.course)
        if len(cuser) != 1:
            raise ValueError('Group ' + str(self) + ' tried to add user ' + str(vsbuser) + ' without an appropriate CourseUser.')
        GroupUser.objects.create(course_user=cuser[0], study_group=self, group_nickname="")
        self.max_users_seen += 1
        self.save()

    def is_building(self):
        return self.max_users_seen <= self.course.build_limit    

    def __str__(self):
        return self.default_name


class GroupInvite(models.Model):
    """
    A temporary object that represents an authorized invite from on user to another.
    """
    sender = models.ForeignKey("GroupUser", on_delete=models.CASCADE)
    recipient = models.ForeignKey("VSBUser", on_delete=models.CASCADE)
    study_group = models.ForeignKey("StudyGroup", on_delete=models.CASCADE)

    def accept(self):
        add = True
        for user in self.study_group.groupuser_set.all():
            if self.recipient == user.course_user.vsb_user:
                add = False
        
        if (add):
            self.recipient.add_course(self.study_group.course) #adds course if it was not in
            self.study_group.add_user(self.recipient)
            self.delete()
        else:
            self.delete()

    def decline(self):
        self.delete()
    
    def __str__(self):
        return "Invite from " + str(self.recipient) + " to group: " + str(self.study_group)


# User Models
class CourseUser(models.Model):
    vsb_user = models.ForeignKey("VSBUser", on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    course_comfort = models.CharField(max_length=32, blank=True) # Each character is in the range (1-5).
    dirty_comfort = models.BooleanField(default=True) #True if the 'course_comfort' needs to be updated.

    def __str__(self):
        return str(self.vsb_user)

class VSBUser(Eventful):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    image = models.ImageField(max_length=4000000, upload_to='media/', blank=True, null=True)
    
    
    
    #available_times = models.BinaryField(max_length=MAX_TIME_BYTES, default=bytearray([0])) #stored in UTC
    available_times = models.JSONField(default='[]')
    utc_timezone_delta = models.IntegerField(default=0) #The -5 in UTC-5:New York #This needs to be changed to a string and implement it throughout the backend
    timezone_string = models.CharField(max_length=50, blank=True, null=True)
    display_name = models.CharField(max_length=50, blank=True, null=True)
    preferred_email = models.CharField(max_length=50, blank=True)   
    institution = models.CharField(max_length=80, blank=True, null=True)
    university =  models.ForeignKey("Institution", on_delete=models.PROTECT, null=True, blank=True)
    def link_artists(apps, schema_editor):
        Album = apps.get_model('discography', 'VSBUser')
        Artist = apps.get_model('discography', 'Institution')
        for album in Album.objects.all():
            artist, created = Artist.objects.get_or_create(name=album.artist)
            album.artist_link = artist
            album.save()
    #groupme = models.CharField(max_length=50, blank=True) ???

    def set_available_times(self, new_times, t_utc_timezone_delta=None):
        """
        Converts the new times to UTC and saves it to available times.
        """
        from . import util
        if type(t_utc_timezone_delta) == type(None): #Defaults to user's timezone
            t_utc_timezone_delta = self.utc_timezone_delta
        converted_times = [new_times[(i + t_utc_timezone_delta*BITS_PER_HOUR) % (MAX_TIME_BYTES*8)] for i in range(8*MAX_TIME_BYTES)]
        self.available_times = util.convert_boolarray_to_available_times_json(converted_times)
        
        self.save()
    
    def get_courses(self):
        return [cuser.course for cuser in self.courseuser_set.all()]

    def get_groupusers(self):
        groupusers = []
        for cuser in self.courseuser_set.all():
            groupusers.extend(cuser.groupuser_set.all())
        return groupusers

    
    

    def add_course(self, course, comfort=None):
        """
        Comfort is assumed to be a string.
        """
        for cuser in self.courseuser_set.all():
            if cuser.course == course:
                return
        if type(comfort) == type(None):
            CourseUser.objects.create(vsb_user=self, course=course, dirty_comfort=True, course_comfort='')
        else:
            CourseUser.objects.create(vsb_user=self, course=course, dirty_comfort=False, course_comfort=comfort)

    def remove_course(self, course):
        for cuser in self.courseuser_set.all():
            if cuser.course == course:
                cuser.delete()

    def get_events(self):
        my_events = set()
        group_events = dict()
        my_events = my_events.union(self.calenderevent_set.all()) #Add personal events
        for cuser in self.courseuser_set.all(): 
            #eset.union(cuser.course.calenderevent_set.all()) #Add course events
            for guser in cuser.groupuser_set.all(): #Add group events
                group_events[guser.study_group.id] = guser.study_group.calenderevent_set.all()

        from .util import EventQuery
        return EventQuery(my_events, group_events)
        


    def __str__(self):
        return self.display_name or str(self.user)

class GroupUser(models.Model):
    course_user = models.ForeignKey(CourseUser, on_delete=models.CASCADE)
    study_group = models.ForeignKey("StudyGroup", on_delete=models.CASCADE)
    group_nickname = models.CharField(max_length=50, blank=True) # if blank, then the name is obtained from the group

    def send_invite(self, vsb_user):
        my_sent_invites = self.groupinvite_set.all()
        #Check to not save multiple invites.
        for inv in my_sent_invites:
            if inv.study_group == self.study_group and inv.recipient == vsb_user:
                return
        GroupInvite.objects.create(sender=self, recipient=vsb_user, study_group=self.study_group)

    def get_groupname(self):
        if self.group_nickname=="":
            return self.study_group.default_name
        return self.group_nickname

    
    def get_groupme_link(self):
        return self.study_group.groupme_link
       

    def __str__(self):
        return str(self.course_user)

    def get_course(self):
        return self.study_group.course

    def get_members(self):
        return self.study_group.groupuser_set.all()

    def remove_guser(self, study_group):
        for guser in self.study_group.groupuser_set.all():
            if guser.study_group == study_group:
                guser.delete()

    def get_user_emails(self):
        if (self.course_user.vsb_user.preferred_email == '' or self.course_user.vsb_user.preferred_email== None):
            return self.course_user.vsb_user.user.email
        return self.course_user.vsb_user.preferred_email

    # Permissions for group

# Calender Models
class CalenderEvent(models.Model):
    time = models.DateTimeField(auto_now=False)
    name = models.CharField(max_length=32, blank=False)
    description = models.TextField(max_length=60, blank=True)
    user = models.ForeignKey(Eventful, on_delete=models.CASCADE)

# Integration Models


class GroupMeIntegration(models.Model): # Stubs for integrating these things.
    study_group = models.OneToOneField("StudyGroup", on_delete=models.CASCADE)
    link = models.CharField(max_length=50, blank=True)
    vsb_user = models.ForeignKey(VSBUser, on_delete=models.CASCADE, null=True)

#Session-like Objects
class MatchSession(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    creation = models.DateTimeField()
    vsb_user = models.ForeignKey(VSBUser, on_delete=models.CASCADE,)
    groups = models.JSONField(default='[]')
    create_allowed = models.BooleanField(default=False)

    class __Data:
        group = None
        score = 0
        comfort_score = 0
        availability_score = 0

        def __init__(self, tup):
            self.group = StudyGroup.objects.get(id=tup[0])
            self.score = str(int((tup[1]))) + '%'
            self.comfort_score = str(int((tup[2]*100))) + '%'
            self.availability_score = str(int((tup[3]*100))) + '%'

    @classmethod
    def create(cls, vsb_user, group_lists, course, create_allowed=False):
        """
        group_lists is a list of tuples with the following structure: (group_id, score, comfort_score, availability_score, building_score)
        """
        return cls(vsb_user=vsb_user, groups=json.dumps(group_lists), creation=timezone.now(), course=course, create_allowed=create_allowed)

    def get_data(self):
        return [
            MatchSession.__Data(tup) for tup in json.loads(self.groups)
        ]

    def get_group_ids(self):
        return [tup[0] for tup in json.loads(self.groups)]

    def check_cleanup(self):
        pass #TODO: implement