from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User


from . import util
from .models import CalenderEvent, VSBUser, MAX_TIME_BYTES, BITS_PER_HOUR, Institution, Course, GroupUser, StudyGroup, CourseUser
from . import matching

import pytz

# Create your tests here.

class Bucket_CalenderEventTests(TestCase):
    def test_event_grouping(self):
        """
        Past events are pruned and events are grouped in a day-by-day basis.
        """
        a_user = User.objects.create()
        user = VSBUser.objects.create(user=a_user)

        today_datetime = timezone.datetime.today()
        today_datetime = timezone.make_aware(timezone.datetime(year=today_datetime.year, month=today_datetime.month, day=today_datetime.day), timezone=timezone.get_default_timezone())
        events = [
            #Past Events
            CalenderEvent.objects.create(user=user,time=today_datetime + timezone.timedelta(days=-7)),
            CalenderEvent.objects.create(user=user,time=today_datetime + timezone.timedelta(days=-1)),
            #Tomorrow's Events
            CalenderEvent.objects.create(user=user,time=today_datetime + timezone.timedelta(days=1)),
            CalenderEvent.objects.create(user=user,time=today_datetime + timezone.timedelta(days=1, hours=12)),
            CalenderEvent.objects.create(user=user,time=today_datetime + timezone.timedelta(days=1, hours=23, minutes=59)),
            #The Following Day's Events
            CalenderEvent.objects.create(user=user,time=today_datetime + timezone.timedelta(days=2)),
            CalenderEvent.objects.create(user=user,time=today_datetime + timezone.timedelta(days=2, hours=12)),
            #Next Month's Events
            CalenderEvent.objects.create(user=user,time=today_datetime + timezone.timedelta(days=30)),
            #Next Year's Events
            CalenderEvent.objects.create(user=user,time=today_datetime + timezone.timedelta(days=365)),
        ]

        received = util.bucket_calenderevents(user.calenderevent_set)

        expected=[
            [
                events[2], events[3], events[4],
            ],
            [
                events[5], events[6],
            ],
            [
                events[7],
            ],
            [
                events[8],
            ],
        ]

        self.assertEqual(received, expected, msg="CalenderEvents.event_grouping:  Order of received events differ from expected.")

    def test_close_to_now(self):
        """
        Ensure events close to now are filtered properly.
        """
        a_user = User.objects.create()
        user = VSBUser.objects.create(user=a_user)

        CalenderEvent.objects.create(user=user, time=timezone.now() + timezone.timedelta(seconds=-5))
        future_event = CalenderEvent.objects.create(user=user, time=timezone.now() + timezone.timedelta(seconds= 5))

        received = util.bucket_calenderevents(user.calenderevent_set)

        self.assertEqual(received, [[future_event]], msg="CalenderEvents.close_to_now:  Close times failed.")

    def test_empty_case(self):
        """
        Ensures a user with nothing is handled properly.
        """
        a_user = User.objects.create()
        user = VSBUser.objects.create(user=a_user)

        received = util.bucket_calenderevents(user.calenderevent_set)

        self.assertEqual(received, [], msg="CalenderEvents.empty_case:  Non-empty list returned.")

    def test_timezones(self):
        """
        Ensures events in the same timezone is kept the same.
        """
        a_user = User.objects.create()
        user = VSBUser.objects.create(user=a_user)

        today_datetime = timezone.datetime.today()
        today_datetime = timezone.datetime(year=today_datetime.year, month=today_datetime.month, day=today_datetime.day)

        tomorrow_late_EST = timezone.make_aware(today_datetime + timezone.timedelta(hours=23), timezone=pytz.timezone('US/Eastern'))
        tomorrow_last_UTC = (tomorrow_late_EST + timezone.timedelta(minutes=10)).astimezone(pytz.utc)
        ETC_event = CalenderEvent.objects.create(user=user, time=tomorrow_late_EST)
        UTC_event = CalenderEvent.objects.create(user=user, time=tomorrow_last_UTC)

        received = util.bucket_calenderevents(user.calenderevent_set)

        self.assertEqual(received, [[ETC_event, UTC_event]], msg="CalenderEvents.timezones:  Timezones failed to align.")

class Bucket_Study_Group_Tests(TestCase):
    def test_adding_study_groups(self):
        a_user = User.objects.create()
        user = VSBUser.objects.create(user=a_user)
        inst = Institution.objects.create(name = "UVA")
        c1 = Course.objects.create(name = "CS 3240", institution= inst)
        sg = StudyGroup.objects.create(default_name="Study Group 1", course=c1)

        expected = 1

        received = len(StudyGroup.objects.all())
        
        self.assertEqual(received, expected, msg="Bucket_Study_Group_test.adding_study_groups:  Adding study groups failed.")

    def test_adding_study_groups_to_class(self):
        a_user = User.objects.create()
        user = VSBUser.objects.create(user=a_user)
        inst = Institution.objects.create(name = "UVA")
        c1 = Course.objects.create(name = "CS 3240", institution= inst)
        c2 = Course.objects.create(name = "CS 3240", institution= inst)
        sg = StudyGroup.objects.create(default_name="Study Group 1", course=c1)
        sg1 = StudyGroup.objects.create(default_name="Study Group 2", course=c2)

        expected = 1

        received = len(StudyGroup.objects.filter(course=c1))
        
        self.assertEqual(received, expected, msg="Bucket_Study_Group_test.adding_study_groups_to_class:  Adding study groups to class failed.")

            
class Bucket_Group_Users_Tests(TestCase):
    def test_adding_group_users_to_study_group(self):
        a_user = User.objects.create()
        user = VSBUser.objects.create(user=a_user)
        inst = Institution.objects.create(name = "UVA")
        c1 = Course.objects.create(name = "CS 3240", institution= inst)
        user.add_course(c1)
        cuser = CourseUser.objects.get(vsb_user=user)
        sg = StudyGroup.objects.create(default_name="Study Group 1", course=c1)
        GroupUser.objects.create(course_user=cuser, group_nickname="CS Kids", study_group=sg)
        GroupUser.objects.create(course_user=cuser, group_nickname="Study Buddies", study_group=sg)

        expected = 2

        received = len(GroupUser.objects.filter(study_group=sg))

        self.assertEqual(received, expected, msg="Bucket_Group_Users_test.adding_group_users_to_study_group:  Adding group users failed.")

    def deleting_user_group_users(self):
        a_user = User.objects.create()
        user = VSBUser.objects.create(user=a_user)
        inst = Institution.objects.create(name = "UVA")
        c1 = Course.objects.create(name = "CS 3240", institution= inst)
        user.add_course(c1)
        cuser = CourseUser.objects.get(vsb_user=user)
        sg = StudyGroup.objects.create(default_name="Study Group 1", course=c1)
        GroupUser.objects.create(course_user=cuser, group_nickname="CS Kids", study_group=sg)
        GroupUser.objects.create(course_user=cuser, group_nickname="Study Buddies", study_group=sg)

        user.delete()

        expected = 0

        received = len(GroupUser.objects.filter(study_group=sg))
        
        self.assertEqual(received, expected, msg="Bucket_Study_Group_test.deleting_user_group_users:  Deleting user and group users failed.")
        
class Convert_Boolarray_To_ByteArrayTests(TestCase):
    def test_convert_boolarray_to_bytearray_empty_list(self):
        """
        Tests that the output of the coversion obeys the empty case.
        """
        input_list = []
        output_barr = util.convert_boolarray_to_bytearray(input_list)

        expected_barr = bytearray()
        self.assertEqual(output_barr, expected_barr, msg="convert_boolarray_to_bytearray: Empty list case failed")

    def test_convert_boolarray_to_bytearray_1_byte(self):
        """
        Tests that a 4-bit array is handles lists less than or equal to one byte.
        """
        input_lists = [ #Recall that these are in LSB on the left.
            [False],
            [True],
            [True, False],
            [True, False, True],
            [True, False, True, False],
            [True, False, True, False, True],
            [True, False, True, False, True, False],
            [True, False, True, False, True, False, True],
            [True, False, True, False, True, False, True, False],
            [False]*8,
            [True]*8
        ]

        output_barrs = []
        for l in input_lists:
            output_barrs.append(util.convert_boolarray_to_bytearray(l))

        expected_barrs = [
            bytearray([0]),
            bytearray([1]),
            bytearray([1]),
            bytearray([5]),
            bytearray([5]),
            bytearray([21]),
            bytearray([21]),
            bytearray([85]),
            bytearray([85]),
            bytearray([0]),
            bytearray([255]),
        ]

        self.assertEqual(output_barrs, expected_barrs, msg="convert_boolarray_to_bytearray: First byte failure.")

    def test_convert_boolarray_to_bytearray_2_bytes(self):
        """
        Tests processing of binary lists from 57 bits to 64 bits.
        """
        input_lists = [ i*[True] for i in range(9, 17)]

        output_barrs = []
        for l in input_lists:
            output_barrs.append(util.convert_boolarray_to_bytearray(l))

        expected_barrs = [
            bytearray([0xff, 0x01]),
            bytearray([0xff, 0x03]),
            bytearray([0xff, 0x07]),
            bytearray([0xff, 0x0f]),
            bytearray([0xff, 0x1f]),
            bytearray([0xff, 0x3f]),
            bytearray([0xff, 0x7f]),
            bytearray([0xff, 0xff]),
        ]

        self.assertEqual(output_barrs, expected_barrs, msg="convert_boolarray_to_bytearray: 2 byte word failure.")

class Convert_ByteArray_To_BoolArrayTests(TestCase):
    def test_empty_case(self):
        input_arr = bytearray()
        output = util.convert_bytearray_to_boolarray(input_arr)
        expected = []

        self.assertEqual(output, expected, msg="convert_bytearray_to_boolarray:  empty case failed")
    
    def test_zero_case(self):
        input_arr = bytearray([0])
        output = util.convert_bytearray_to_boolarray(input_arr)
        expected = [False]*8

        self.assertEqual(output, expected, msg="convert_bytearray_to_boolarray:  zero case failed")

    def test_one_case(self):
        input_arr = bytearray([1])
        output = util.convert_bytearray_to_boolarray(input_arr)
        expected = [True, False, False, False, False, False, False, False]

        self.assertEqual(output, expected, msg="convert_bytearray_to_boolarray:  one case failed")

    def test_full_case(self):
        input_arr = bytearray([255])
        output = util.convert_bytearray_to_boolarray(input_arr)
        expected = [True]*8

        self.assertEqual(output, expected, msg="convert_bytearray_to_boolarray:  full case failed")

    def test_multibyte(self):
        input_arr = bytearray([0, 1, 16, 255])
        output = util.convert_bytearray_to_boolarray(input_arr)
        expected = 8*[False]
        expected.extend([True, False, False, False, False, False, False, False])
        expected.extend([False, False, False, False, True, False, False, False])
        expected.extend(8*[True])

        self.assertEqual(output, expected, msg="convert_bytearray_to_boolarray:  multibyte case failed")

class Convert_Comfort_String_To_Float_ArrayTests(TestCase):
    def test_empty_case(self):
        input_str=""
        output = util.convert_comfort_string_to_float_array(input_str)
        expected = []
        self.assertEqual(output, expected, msg="convert_confort_string_to_float_array:  empty test case")

    def test_single_string(self):
        input_str="4"
        output = util.convert_comfort_string_to_float_array(input_str)
        expected = [4]
        self.assertEqual(output, expected, msg="convert_confort_string_to_float_array:  single test case")

    def test_multiple_string(self):
        input_str="012345678910"
        output = util.convert_comfort_string_to_float_array(input_str)
        expected = [0,1,2,3,4,5,6,7,8,9,1,0]
        self.assertEqual(output, expected, msg="convert_confort_string_to_float_array:  multiple test case")

class VSBUserTests(TestCase):
    #set_available_times
    def test_set_available_times_zeros(self):
        a_user = User.objects.create()
        vsbuser = VSBUser.objects.create(user=a_user)

        new_times = [False]*MAX_TIME_BYTES*8
        expected_output = util.convert_boolarray_to_available_times_json(new_times)

        vsbuser.set_available_times(new_times)

        self.assertEqual(vsbuser.available_times, expected_output, msg="VSBUsers.set_available_times: Zero time availablility failed.")

    def test_set_available_times_ones(self):
        a_user = User.objects.create()
        vsbuser = VSBUser.objects.create(user=a_user)

        new_times = [True]*MAX_TIME_BYTES*8
        expected_output = util.convert_boolarray_to_available_times_json(new_times)

        vsbuser.set_available_times(new_times)

        self.assertEqual(vsbuser.available_times, expected_output, msg="VSBUsers.set_available_times: Full time availablility failed.")

    def test_set_available_times_utc_0(self):
        a_user = User.objects.create()
        vsbuser = VSBUser.objects.create(user=a_user)

        new_times = [(i >= BITS_PER_HOUR*9 and i < BITS_PER_HOUR*17) for i in range(MAX_TIME_BYTES*8)]
        expected_time_hours = [
            False, False, False, False, False, False, False, False, 
            False, True, True, True, True, True, True, True, 
            True, False, False, False, False, False, False, False]
        expected_time_hours.extend(6*24*[0])
        expected_times = [expected_time_hours[i // BITS_PER_HOUR] for i in range(BITS_PER_HOUR*len(expected_time_hours))]
        expected_output = util.convert_boolarray_to_available_times_json(expected_times)

        vsbuser.set_available_times(new_times)

        self.assertEqual(vsbuser.available_times, expected_output, msg="VSBUsers.set_available_times: UTC normal time availablility failed.")


    def test_set_available_times_utc_n5(self):
        a_user = User.objects.create()
        vsbuser = VSBUser.objects.create(user=a_user)

        new_times = [(i >= BITS_PER_HOUR*9 and i < BITS_PER_HOUR*17) for i in range(MAX_TIME_BYTES*8)]
        expected_time_hours = [
            False, False, False, False, False, False, False, False, 
            False, False, False, False, False, False, True, True, 
            True, True, True, True, True, True, False, False]
        expected_time_hours.extend(6*24*[False])
        expected_times = [expected_time_hours[i // BITS_PER_HOUR] for i in range(BITS_PER_HOUR*len(expected_time_hours))]
        expected_output = util.convert_boolarray_to_available_times_json(expected_times)

        vsbuser.set_available_times(new_times, -5)

        self.assertEqual(vsbuser.available_times, expected_output, msg="VSBUsers.set_available_times: UTC-5 normal time availablility failed.")

    def test_set_available_times_user_utc_n5(self):
        a_user = User.objects.create()
        vsbuser = VSBUser.objects.create(user=a_user, utc_timezone_delta=-5)

        new_times = [(i >= BITS_PER_HOUR*9 and i < BITS_PER_HOUR*17) for i in range(MAX_TIME_BYTES*8)]
        expected_time_hours = [
            False, False, False, False, False, False, False, False, 
            False, False, False, False, False, False, True, True, 
            True, True, True, True, True, True, False, False]
        expected_time_hours.extend(6*24*[False])
        expected_times = [expected_time_hours[i // BITS_PER_HOUR] for i in range(BITS_PER_HOUR*len(expected_time_hours))]
        expected_output = util.convert_boolarray_to_available_times_json(expected_times)

        vsbuser.set_available_times(new_times)

        self.assertEqual(vsbuser.available_times, expected_output, msg="VSBUsers.set_available_times: UTC-5 normal time availablility failed.")
    
    def test_get_events(self):
        inst = Institution.objects.create(name="test")
        course = Course.objects.create(name="test", institution=inst, build_limit=4, topics="a;b;c;")
        groups = StudyGroup.objects.create(course=course, default_name="test")

        a_user = User.objects.create()
        vsbuser = VSBUser.objects.create(user=a_user, utc_timezone_delta=-5)
        CourseUser.objects.create(course = course, vsb_user=vsbuser)
        groups.add_user(vsbuser)

        c1 = CalenderEvent.objects.create(name="Event1", user=vsbuser, time=timezone.make_aware(timezone.datetime(year=2020, month=1, day=1, hour=12), timezone=timezone.get_default_timezone()))
        c2 = CalenderEvent.objects.create(name="Event2", user=vsbuser, time=timezone.make_aware(timezone.datetime(year=2020, month=1, day=2, hour=12), timezone=timezone.get_default_timezone()))
        c3 = CalenderEvent.objects.create(name="Event3", user=groups, time=timezone.make_aware(timezone.datetime(year=2020, month=1, day=3, hour=12), timezone=timezone.get_default_timezone()))
        c4 = CalenderEvent.objects.create(name="Event4", user=vsbuser, time=timezone.make_aware(timezone.datetime(year=2020, month=1, day=4, hour=12), timezone=timezone.get_default_timezone()))
        c5 = CalenderEvent.objects.create(name="Event5", user=groups, time=timezone.make_aware(timezone.datetime(year=2020, month=1, day=5, hour=12), timezone=timezone.get_default_timezone()))

        querry = vsbuser.get_events()

        self.assertEqual(querry.all(), {c1, c2, c3, c4, c5}, msg="VSBUsers.get_events().all() failed")
        self.assertEqual(querry.vsb_user(), {c1, c2, c4}, msg="VSBUsers.get_events().vsb_user() failed")
        self.assertEqual(querry.group(groups), {c3, c5}, msg="VSBUsers.get_events().group() failed")
        self.assertEqual(querry.all_groups(), {c3, c5}, msg="VSBUsers.get_events().all_groups() failed")

class CourseEditingTests(TestCase):
    n = 4

    @staticmethod
    def create_vsb_users(inst, users, course, comfort_arr):
        users = [VSBUser.objects.create(user=users[i], institution=inst) for i in range(CourseEditingTests.n)]
        for i in range(len(users)):
            users[i].add_course(course, comfort_arr[i])
        return users

    @staticmethod
    def create_group_users(cusers, group):
        return [GroupUser.objects.create(course_user=cusers[i], study_group=group) for i in range(len(cusers))]

    @staticmethod
    def common_utility():
        inst = Institution.objects.create(name="test")
        users = [User.objects.create(first_name=str(i), last_name="test", username=str(i)) for i in range(CourseEditingTests.n)]
        return (inst, users)

    def test_encoding_empty(self):
        (inst, _) = CourseEditingTests.common_utility()
        course1 = Course.objects.create(name="test", institution=inst, build_limit=4, topics='')
        course2 = Course.objects.create(name="test", institution=inst, build_limit=4, topics=';')
        course3 = Course.objects.create(name="test", institution=inst, build_limit=4, topics="one;two;three;")

        topic = ""
        course1.add_topic(topic)
        course2.add_topic(topic)
        course3.add_topic(topic)
        output1 = course1.get_topics()
        output2 = course2.get_topics()
        output3 = course3.get_topics()

        expected1 = []
        expected2 = ['']
        expected3 = ["one", "two", "three"]

        self.assertEqual(output1, expected1, msg="CourseEditing encoding:  empty case failed for emptier object")
        self.assertEqual(output2, expected2, msg="CourseEditing encoding:  empty case failed for empty object")
        self.assertEqual(output3, expected3, msg="CourseEditing encoding:  empty case failed for filled object")
    
    def test_encoding_one(self):
        (inst, _) = CourseEditingTests.common_utility()
        course1 = Course.objects.create(name="test", institution=inst, build_limit=4, topics='')
        course2 = Course.objects.create(name="test", institution=inst, build_limit=4, topics=';')
        course3 = Course.objects.create(name="test", institution=inst, build_limit=4, topics="one;two;three;")
        topic = "testadd"
        course1.add_topic(topic)
        course2.add_topic(topic)
        course3.add_topic(topic)
        output1 = course1.get_topics()
        output2 = course2.get_topics()
        output3 = course3.get_topics()

        expected1 = ['testadd']
        expected2 = ['', 'testadd']
        expected3 = ["one", "two", "three", 'testadd']

        self.assertEqual(output1, expected1, msg="CourseEditing encoding:  one case failed for emptier object")
        self.assertEqual(output2, expected2, msg="CourseEditing encoding:  one case failed for empty object")
        self.assertEqual(output3, expected3, msg="CourseEditing encoding:  one case failed for filled object")

    def test_removing(self):
        (inst, _) = CourseEditingTests.common_utility()
        course1 = Course.objects.create(name="test", institution=inst, build_limit=4, topics='')
        course2 = Course.objects.create(name="test", institution=inst, build_limit=4, topics='one;two;three;four;')
        course3 = Course.objects.create(name="test", institution=inst, build_limit=4, topics="one;two;three;")
        topic = "four"
        course1.remove_topic(topic)
        course2.remove_topic(topic)
        course3.remove_topic(topic)
        output1 = course1.get_topics()
        output2 = course2.get_topics()
        output3 = course3.get_topics()

        expected1 = []
        expected2 = ["one", "two", "three"]
        expected3 = ["one", "two", "three"]

        self.assertEqual(output1, expected1, msg="CourseEditing removing:  one case failed for emptier object")
        self.assertEqual(output2, expected2, msg="CourseEditing removing:  one case failed for contained, filled object")
        self.assertEqual(output3, expected3, msg="CourseEditing removing:  one case failed for non-contained, filled object")

    def test_rename(self):
        (inst, _) = CourseEditingTests.common_utility()
        course1 = Course.objects.create(name="test", institution=inst, build_limit=4, topics='')
        course2 = Course.objects.create(name="test", institution=inst, build_limit=4, topics='one;two;three;')
        course3 = Course.objects.create(name="test", institution=inst, build_limit=4, topics="one;three;")
        old_name = "two"
        new_name = "2"
        course1.rename_topic(old_name, new_name)
        course2.rename_topic(old_name, new_name)
        course3.rename_topic(old_name, new_name)
        output1 = course1.get_topics()
        output2 = course2.get_topics()
        output3 = course3.get_topics()

        expected1 = []
        expected2 = ["one", "2", "three"]
        expected3 = ["one", "three"]

        self.assertEqual(output1, expected1, msg="CourseEditing renaming:  one case failed for emptier object")
        self.assertEqual(output2, expected2, msg="CourseEditing renaming:  one case failed for contained, filled object")
        self.assertEqual(output3, expected3, msg="CourseEditing renaming:  one case failed for non-contained, filled object")
    
    def test_adding_with_users(self):
        (inst, users) = CourseEditingTests.common_utility()
        course = Course.objects.create(name="test", institution=inst, build_limit=4, topics='one;two;three;')


        comfort_arr = [
            "000",
            "999",
            "000",
            "999"
        ]
        users_per_group = 2
        group_count = 2
        groups=[ StudyGroup.objects.create(course=course, default_name="test") for _ in range(group_count) ]

        vsbusers = CourseEditingTests.create_vsb_users(inst, users, course, comfort_arr)
        cusers = [vsbuser.courseuser_set.all()[0] for vsbuser in vsbusers]

        gusers = []
        for i in range(group_count):
            m = users_per_group*i
            users = [ vsbusers[i] for i in range(m, m + users_per_group) ]
            gusers.extend(CourseEditingTests.create_group_users(cusers, groups[i]))
        gusers_id = [user.id for user in gusers] #This is needed b/c the database does not update gusers

        course.add_topic('test')

        for id in gusers_id:
            guser = GroupUser.objects.filter(id=id)[0]

            self.assertTrue(guser.course_user.dirty_comfort, msg="CourseEditing encoding sideffect: test case failed for " + str(guser))

    def test_omit_adding_with_users(self):
        (inst, users) = CourseEditingTests.common_utility()
        course = Course.objects.create(name="test", institution=inst, build_limit=4, topics='one;two;three;')

        users_per_group = 2
        group_count = 2
        groups=[ StudyGroup.objects.create(course=course, default_name="test") for _ in range(group_count) ]

        comfort_arr = [
            "000",
            "999",
            "000",
            "999"
        ]
        vsbusers = CourseEditingTests.create_vsb_users(inst, users, course, comfort_arr)
        cusers = [vsbuser.courseuser_set.all()[0] for vsbuser in vsbusers]

        gusers = []
        for i in range(group_count):
            m = users_per_group*i
            users = [ vsbusers[i] for i in range(m, m + users_per_group) ]
            gusers.extend(CourseEditingTests.create_group_users(cusers, groups[i]))
        gusers_id = [user.id for user in gusers] #This is needed b/c the database does not update gusers

        course.add_topic('one')

        for id in gusers_id:
            guser = GroupUser.objects.filter(id=id)[0]
            self.assertFalse(guser.course_user.dirty_comfort, msg="CourseEditing encoding omission sideffect: test case failed for " + str(guser))

    def test_remove_with_users(self):
        (inst, users) = CourseEditingTests.common_utility()
        course = Course.objects.create(name="test", institution=inst, build_limit=4, topics='one;two;three;')

        users_per_group = 2
        group_count = 2
        groups=[ StudyGroup.objects.create(course=course, default_name="test") for _ in range(group_count) ]

        comfort_arr = [
            "012",
            "012",
            "012",
            "012"
        ]
        vsbusers = CourseEditingTests.create_vsb_users(inst, users, course, comfort_arr)
        cusers = [vsbuser.courseuser_set.all()[0] for vsbuser in vsbusers]

        gusers = []
        expected_arr = "12"
        for i in range(group_count):
            m = users_per_group*i
            users = [ vsbusers[i] for i in range(m, m + users_per_group) ]
            gusers.extend(CourseEditingTests.create_group_users(cusers, groups[i]))
        gusers_id = [user.id for user in gusers] #This is needed b/c the database does not update gusers

        course.remove_topic('one')

        for id in gusers_id:
            guser = GroupUser.objects.filter(id=id)[0]
            self.assertEqual(guser.course_user.course_comfort, expected_arr, msg="CourseEditing removal sideffect: test case failed for " + str(guser))

    def test_rename_with_users(self):
        (inst, users) = CourseEditingTests.common_utility()
        course = Course.objects.create(name="test", institution=inst, build_limit=4, topics='one;two;three;')

        users_per_group = 2
        group_count = int(CourseEditingTests.n/users_per_group)
        groups=[ StudyGroup.objects.create(course=course, default_name="test") for _ in range(group_count) ]

        comfort_arr = [
            "012",
            "012",
            "012",
            "012"
        ]
        vsbusers = CourseEditingTests.create_vsb_users(inst, users, course, comfort_arr)
        cusers = [vsbuser.courseuser_set.all()[0] for vsbuser in vsbusers]

        gusers = []
        expected_arr = "012"
        for i in range(group_count):
            m = users_per_group*i
            users = [ vsbusers[i] for i in range(m, m + users_per_group) ]
            gusers.extend(CourseEditingTests.create_group_users(cusers, groups[i]))
        gusers_id = [user.id for user in gusers] #This is needed b/c the database does not update gusers

        course.rename_topic('one','1')

        for id in gusers_id:
            guser = GroupUser.objects.filter(id=id)[0]
            self.assertEqual(guser.course_user.course_comfort, expected_arr, msg="CourseEditing removal sideffect: test case failed for " + str(guser))

class GroupInviteTests(TestCase):
    def test_accept(self):
        r = range(2)

        inst = Institution.objects.create(name="test")
        course = Course.objects.create(name="test", institution=inst, build_limit=4, topics="")
        group = StudyGroup.objects.create(course=course, default_name="test")
        users = [User.objects.create(first_name=str(i), last_name="test", username=str(i)) for i in r]
        vsbusers = [VSBUser.objects.create(user=users[i], institution=inst, available_times="'\"\"") for i in r]
        vsbusers[0].add_course(course)
        guser = GroupUser.objects.create(course_user=vsbusers[0].courseuser_set.filter(course=course)[0], study_group=group)

        guser.send_invite(vsbusers[1])

        invite = vsbusers[1].groupinvite_set.all()[0]
        invite.accept()

        group = StudyGroup.objects.filter(id=group.id).all()[0]
        vsbusers[1] = VSBUser.objects.filter(id=vsbusers[1].id).all()[0]
        
        self.assertEqual(len(group.groupuser_set.all()), 2, msg="GroupInvite accept:  group count mismatch")
        self.assertEqual(vsbusers[1].get_groupusers()[0].study_group, group, msg="GroupInvite accept: created GroupUser mismatch")

    def test_reject(self):
        r = range(2)

        inst = Institution.objects.create(name="test")
        course = Course.objects.create(name="test", institution=inst, build_limit=4, topics="")
        group = StudyGroup.objects.create(course=course, default_name="test")
        users = [User.objects.create(first_name=str(i), last_name="test", username=str(i)) for i in r]
        vsbusers = [VSBUser.objects.create(user=users[i], institution=inst, available_times="'\"\"") for i in r]
        vsbusers[0].add_course(course)
        guser = GroupUser.objects.create(course_user=vsbusers[0].courseuser_set.filter(course=course)[0], study_group=group)

        guser.send_invite(vsbusers[1])

        invite = vsbusers[1].groupinvite_set.all()[0]
        invite.decline()

        group = StudyGroup.objects.filter(id=group.id).all()[0]
        self.assertEqual(len(group.groupuser_set.all()), 1, msg="GroupInvite deny:  group count mismatch")

class MatchingTest(TestCase):
    def test_composition_rank(self):
        user_count = 5
        comfort = "511"
        timezones = [False, False, True, False, False, False, False, False]
        timezones.extend([False]*(MAX_TIME_BYTES*8 - 8))
        timezones= util.convert_boolarray_to_available_times_json(timezones)

        inst = Institution.objects.create(name="test")
        course = Course.objects.create(name="test", institution=inst, build_limit=4, topics="a;b;c;")
        groups = [StudyGroup.objects.create(course=course, default_name="test" + str(i)) for i in range(user_count - 1)]
        users = [User.objects.create(first_name=str(i), last_name="test", username=str(i)) for i in range(user_count)]
        vsbusers = [VSBUser.objects.create(user=users[i], institution=inst, available_times=timezones) for i in range(user_count)]
   
        for index_group in range(user_count - 1):
            vsbusers[index_group].add_course(course, comfort)
            for index_user in range(index_group + 1):
                groups[index_group].add_user(vsbusers[index_user])

        (scoring, _) = matching.generate_matching_groups(vsbusers[-1], course, comfort)

        output_groups = [score.get_group() for score in scoring]

        expected_order = [
            groups[1],
            groups[2],
            groups[0],
            #groups[3], This is filtered out due build limit being reached
        ]

        self.assertEquals(output_groups, expected_order, msg="MatchingTest: user count test failed")

    def test_times_rank(self):
        user_count = 4
        comfort = "511"
        timezones = [[] for _ in range(3)]
        timezones[0] = [True, True, True, False, False, False, False, False]
        timezones[1] = [False, False, True, False, False, False, False, False]
        timezones[2] = [True, True, False, False, False, False, False, False]

        timezones[0].extend([False]*(MAX_TIME_BYTES*8 - 8))
        timezones[1].extend([False]*(MAX_TIME_BYTES*8 - 8))
        timezones[2].extend([False]*(MAX_TIME_BYTES*8 - 8))

        timezones[0]= util.convert_boolarray_to_available_times_json(timezones[0])
        timezones[1]= util.convert_boolarray_to_available_times_json(timezones[1])
        timezones[2]= util.convert_boolarray_to_available_times_json(timezones[2])

        inst = Institution.objects.create(name="test")
        course = Course.objects.create(name="test", institution=inst, build_limit=4, topics="a;b;c;")
        groups = [StudyGroup.objects.create(course=course, default_name="test" + str(i)) for i in range(user_count - 1)]
        users = [User.objects.create(first_name=str(i), last_name="test", username=str(i)) for i in range(user_count)]
        vsbusers = [VSBUser.objects.create(user=users[i], institution=inst, available_times=timezones[i%3]) for i in range(user_count)]
   
        for index_group in range(user_count - 1):
            vsbusers[index_group].add_course(course, comfort)
            groups[index_group].add_user(vsbusers[index_group])

        (scoring, _) = matching.generate_matching_groups(vsbusers[-1], course, comfort)

        output_groups = [score.get_group() for score in scoring]

        expected_order = [
            groups[0],
            groups[2],
            groups[1],
        ]

        self.assertEquals(output_groups, expected_order, msg="MatchingTest: user times test failed")
    
    def test_helping_rank(self):
        user_count = 5
        comfort = [
            "511",
            "211",
            "311",
            "113",
        ]
        timezones = [False, False, True, False, False, False, False, False]
        timezones.extend([False]*(MAX_TIME_BYTES*8 - 8))
        timezones= util.convert_boolarray_to_available_times_json(timezones)

        inst = Institution.objects.create(name="test")
        course = Course.objects.create(name="test", institution=inst, build_limit=4, topics="a;b;c;")
        groups = [StudyGroup.objects.create(course=course, default_name="test" + str(i)) for i in range(user_count - 1)]
        users = [User.objects.create(first_name=str(i), last_name="test", username=str(i)) for i in range(user_count)]
        vsbusers = [VSBUser.objects.create(user=users[i], institution=inst, available_times=timezones) for i in range(user_count)]
        
        for index_group in range(user_count - 1):
            vsbusers[index_group].add_course(course, comfort[index_group])
            groups[index_group].add_user(vsbusers[index_group])

        (scoring, _) = matching.generate_matching_groups(vsbusers[-1], course, comfort[0])

        output_groups = [score.get_group() for score in scoring]

        expected_order = [
            groups[0],
            groups[2],
            groups[1],
            groups[3],
        ]

        self.assertEquals(output_groups, expected_order, msg="MatchingTest: user helping test failed")
        
class Bucket_Course_And_Topic_Tests(TestCase):

    def test_inserting_course(self):
        """
        Ensure courses are added correctly.
        """
        a_user = User.objects.create(first_name="2", last_name="test", username="test")
        user = VSBUser.objects.create(user=a_user)
        inst = Institution.objects.create(name = "UVA")
        c1 = Course.objects.create(name = "CS 3240", institution= inst)
        c2 = Course.objects.create(name = "CS 1110", institution= inst)

        user.add_course(c1)
        user.add_course(c2)

        expected = 2

        received = len(user.get_courses())

        self.assertEqual(received, expected, msg="Course_And_Topic.inserting_course:  Adding courses failed.")

    def test_removing_course(self):
        """
        Ensures a user can remove a course properly.
        """
        a_user = User.objects.create(first_name="2", last_name="test", username="test")
        user = VSBUser.objects.create(user=a_user)
        inst = Institution.objects.create(name = "UVA")
        c1 = Course.objects.create(name = "CS 3240", institution= inst)
        c2 = Course.objects.create(name = "CS 1110", institution= inst)

        user.add_course(c1)
        user.add_course(c2)
        user.remove_course(c1)

        expected = 1

        received = len(user.get_courses())

        self.assertEqual(received, expected, msg="Course_And_Topic.removing_course:  Removing courses failed.")

    def test_adding_duplicate_course(self):
        """
        Ensures events in the same timezone is kept the same.
        """
        a_user = User.objects.create(first_name="2", last_name="test", username="test")
        user = VSBUser.objects.create(user=a_user)
        inst = Institution.objects.create(name = "UVA")
        c1 = Course.objects.create(name = "CS 3240", institution= inst)

        user.add_course(c1)
        user.add_course(c1)

        expected = 1

        received = len(user.get_courses())

        self.assertEqual(received, expected, msg="Course_And_Topic.adding_duplicate_course:  Adding duplicate course test failed.")
           
