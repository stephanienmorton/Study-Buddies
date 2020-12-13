import datetime
from operator import attrgetter

from django.utils import timezone
from django.contrib.auth.models import User
from django.urls import reverse

import numpy
import pytz
import json



TIME_ZONE_CHOICES = [(x, x) for x in pytz.common_timezones]

def get_utcdelta_from_tzinfo(tzinfo):
    """
    Assumes tzinfo is a pytz.tzinfo object
    """
    delta = tzinfo._utcoffset
    return int(round( 24*delta.days + delta.seconds/3600 ))


class EventQuery:
    __user = set()
    __group = dict() #Stores events by group id

    def all(self):
        rset = self.__user
        return rset.union(self.all_groups())

    def vsb_user(self):
        return self.__user

    def group(self, group):
        return set(self.__group.get(group.id))

    def all_groups(self):
        rset = set()
        for index in self.__group:
            rset = rset.union(self.__group[index])
        return rset

    def __init__(self, user_events, group_event_dictionary):
        self.__user = user_events
        self.__group = group_event_dictionary


def bucket_calenderevents (event_querry_set):
    #Get only upcoming events
    upcoming_events = set()
    if type(event_querry_set) == set:
        tz = timezone.now()
        for event in event_querry_set:
            if event.time >= tz:
                upcoming_events.add(event)
    else:
        upcoming_events = event_querry_set.filter(time__gte=timezone.now())
    event_list = []
    for event in upcoming_events:
        #Do timezone conversion
        event.time = event.time.astimezone(timezone.get_default_timezone())
        event_list.append(event)

    if len(event_list) == 0:
        return []

    #Sort the events
    event_list.sort(key=attrgetter('time'))


    #Sort the events into daily buckets
    event_buckets = []
    current_bucket = [event_list[0]]
    for i in range(1, len(event_list)):
        event = event_list[i]

        if current_bucket[0].time.date() != event.time.date():
            event_buckets.append(current_bucket)
            current_bucket = [event]
        else:
            current_bucket.append(event)
    event_buckets.append(current_bucket)

    return event_buckets


def get_common_context(context, request, active_index):
    """
    Sets the common context for views and returns the User and VSBUser for the request.
    """
    from .models import VSBUser

    context['logout_redirect'] = reverse('VSB:home')
    context['active_index'] = active_index

    try:
        f_user = User.objects.get(id=request.user.id)
        vsbuser = VSBUser.objects.get(user=f_user)
    except:
        f_user = None
        vsbuser = None

    try:
        context['icon'] = vsbuser.image.url
    except:
        pass

    return (f_user, vsbuser)


def convert_boolarray_to_available_times_json(boolarr):
    return json.dumps([b and 1 or 0 for b in boolarr])

def convert_available_times_json_to_boolarray(json_text):
    return [c == 1 for c in json.loads(json_text)]



#legacy code
def convert_boolarray_to_bytearray(boolarray):
        """
        Note that the bool array is read such that index 0 is the LSB.
        """
        byte_size = (int)(numpy.ceil(len(boolarray) / 8))
        arr = bytearray(byte_size)
        left = len(boolarray)
        for n_byte in range(byte_size):
            value = 0
            limit = min(8, left) #Processes up to 8 bits at a time
            left -= limit
            for bit in range(limit):
                index = n_byte*8 + bit
                if boolarray[index]:
                    value += 2**bit #inefficient, but fine
            arr[n_byte] = value

        return arr
def convert_bytearray_to_boolarray(bytearr):
    """
    Note that the returned array is LSB first.  The byte array is assumed to be stored in little endian.
    """
    arr = [False for _ in range(8*len(bytearr))]
    for i in range(len(bytearr)):
        mask = 1
        for j in range(8):
            arr[8*i + j] = (bytearr[i] & mask) > 0
            mask <<= 1

    return arr
def convert_memoryview_to_bytearray(memview):
    ints = [int.from_bytes(memview[i], 'little') for i in range(len(memview))]
    return bytearray(ints)

def convert_comfort_string_to_float_array(comfort_string):
    """
    Assumes the comfort levels are integers 0, 1, 2, 3, 4, 5, 6, 7, 8, or 9.
    """
    arr = []
    for c in comfort_string:
        arr.append(float(c))
    return arr