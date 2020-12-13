from django.shortcuts import render, get_object_or_404
from django.views import generic
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from django.forms import ModelForm, Form
from django.contrib.auth.decorators import login_required
import groupy
from groupy import Client
import requests
import time


from .models import StudyGroup, CalenderEvent, Course, VSBUser, DAY_BYTES, MatchSession, Institution, GroupMeIntegration, GroupInvite
from .forms import MakeAccountForm, ClassForm, TimeZoneAvailability, DateAvaliabilityForm, InviteForm, InstitutionForm

from . import util
from . import matching

from enum import Enum
import datetime
import logging
import pytz



class ActiveIndex(Enum):
    MATCHED = 0
    GROUPS = 1
    SCHEDULE = 2
    SETTINGS = 3

SETTINGS_FORM_DICTIONARY_Prime = {
        'group':0,
        'Time Zone':1,
        'Availability Long':2,
        'Availability Daily':3,
        'Profile':4,
    }

# Create your views here.





def authenticate(request, group_id):
    
    f_user = User.objects.get(id=request.user.id)
    vsbuser = VSBUser.objects.get(user=f_user) 
    group = StudyGroup.objects.get(id=group_id)
    try:
        GroupMeIntegration.objects.create(study_group=group, vsb_user=vsbuser)
    except:
        pass
    path = "https://oauth.groupme.com/oauth/authorize?client_id=wbjg6zQAOi5imLoZkIPNCfK4tXaxNVsdkrCJky7gZmpF8quU"
    return HttpResponseRedirect(path)


def token(request):
 
    url= request.get_full_path()
    token = url[39:]
    f_user = User.objects.get(id=request.user.id)
    vsbuser = VSBUser.objects.get(user=f_user)    
    for group in GroupMeIntegration.objects.filter(vsb_user=vsbuser):
        study_group = StudyGroup.objects.get(default_name=group.study_group)
        client = Client.from_token(token)
        new_group = client.groups.create(name=study_group.default_name, description="", share=True)
        study_group.groupme_link = new_group.share_url
        study_group.save()
        group.delete()    
    return HttpResponseRedirect(reverse('VSB:account_groups'))

def groupme_link(request, group_id):
    study_group = StudyGroup.objects.get(id=group_id)
    link = study_group.groupme_link
    return HttpResponseRedirect(link)



class GroupView(generic.TemplateView):
    template_name = "VSB/group.html"


#Account views
#Account settings view
class AccountSettingsView(generic.DetailView):
    model = User
    template_name = "VSB/settings.html"

    def get_object(self, queryset=None):
        return self.request.user
        
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (f_user, vsbuser) = util.get_common_context(context, self.request, ActiveIndex.SETTINGS.value)
        context['form2'] = ClassForm    
        context['time_zone_form'] = TimeZoneAvailability
        context['availability_form'] = DateAvaliabilityForm
        context['logout_redirect'] = reverse('VSB:home')
        context['alert'] = self.request.GET.get('alert', "")
        try:
            
            context['form'] = MakeAccountForm(instance=vsbuser)
            context['institution_form'] = InstitutionForm(instance=vsbuser)
       
         
            context['courses'] = vsbuser.get_courses() 
            context['utc'] = vsbuser.utc_timezone_delta
            context['timezone_string'] = vsbuser.timezone_string
        except:
            context['courses'] = ['An internal error occurred.']
            context['form'] = ['An internal error occurred.']
            context['institution_form'] = ['An internal error occured']
           

        try:
            barr = util.convert_available_times_json_to_boolarray(vsbuser.available_times) #This will error when the availability is not set yet.
            s = ""
            for t in barr:
                if t:
                    s += 'T'
                else:
                    s += 'F'
            context['avail'] = s
        except:
            context['avail'] = "No availability data provided."
            pass #TODO
        return context


def save_changes(request):
    alert = ""
    try:
        f_user = User.objects.get(id=request.user.id)
        vsbuser = VSBUser.objects.get(user=f_user)    
        if request.method == "POST":
            form_type = request.POST['settings_form_type']
            edit_form = MakeAccountForm(data= request.POST, instance=vsbuser, files=request.FILES or None)
            institution_form = InstitutionForm(request.POST, instance=vsbuser)
            if form_type == 'group':
                pass
            elif form_type =='Time Zone' and request.POST['TZ'] != '':
                try:
                    tzinfo = pytz.timezone(request.POST['TZ'])
                    vsbuser.timezone_string = tzinfo
                    utc_delta = util.get_utcdelta_from_tzinfo(tzinfo)
                    vsbuser.utc_timezone_delta = utc_delta
                    vsbuser.save()
                    alert += "?alert=Successfully saved timezone!"
                except:
                    alert += "?alert=Error! Timezone not saved."
                    
            elif form_type == 'Availability Daily':
                boolarr = []
                names = ['InMonday,', 'InTuesday,', 'InWednesday,', 'InThursday,', 'InFridays,', 'InSaturday,', 'InSunday,']
                for name in names:
                    day = [0 for _ in range(24)]    
                    for i in range(24):
                        value = request.POST.get(name + str(i), None)
                        if value:
                            day[i] = 1

                    boolarr.extend(
                        day
                    )
                vsbuser.set_available_times(boolarr)
                alert += "?alert=Successfully saved availability!"
            elif form_type == 'Profile' and edit_form.is_valid():
                print("in profile")
                edit_form.save()
                alert += "?alert=Successfully saved profile!"
                    

            elif form_type == 'University' and institution_form.is_valid():
                print("hello")
                college = request.POST.get("university")
                college1 = Institution.objects.get(id=college)
                vsbuser.university=college1
                vsbuser.save()   
    except:
        pass
    return HttpResponseRedirect(reverse('VSB:account_settings') + alert)

class AccountComfortView(generic.TemplateView):
    template_name="VSB/comfort_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (_, vsbuser) = util.get_common_context(context, self.request, ActiveIndex.SETTINGS.value)
        try:
            course_id = int(self.request.GET['course_id'])
            course = Course.objects.get(id=course_id)
            c_user = vsbuser.courseuser_set.get(course=course)

            vsbuser.courseuser_set.filter(course=course)[0] #If this errors, then we know that the user does not have the course
            context['course_id'] = course_id
            current_comfort = c_user.course_comfort
            topics = course.get_topics()
            if c_user.dirty_comfort:
                current_comfort= "1"*len(topics)
            context['topics'] = [(current_comfort[i], topics[i]) for i in range(len(topics))]
        except:
            pass #TODO: Implement somthing to show error

        return context

def save_comfort(request):
    f_user = User.objects.get(id=request.user.id)
    vsbuser = VSBUser.objects.get(user=f_user)

    alert = ""
    course_id = request.POST.get('course_id', None)
    print(course_id)
    if course_id:
        course_id = int(course_id)
        course = Course.objects.get(id=course_id)
        if course and course in vsbuser.get_courses():
            c_user = vsbuser.courseuser_set.get(course=course)
            topics = course.get_topics()
            s = ""
            for i in range(len(topics)):
                s += str(request.POST.get("topic" + str(i)))
            print(s)
            c_user.course_comfort = s
            c_user.dirty_comfort = False
            c_user.save()
            if request.POST.get('match') == '1':
                return match(request)
            alert += "?alert=Successfully saved comfort!"

    return HttpResponseRedirect(reverse('VSB:account_settings') + alert)

#Account/Schedule views
class AccountScheduleView(generic.DetailView): #BUG: do not allow vsbuser to delete group events
    model = User
    template_name = "VSB/schedule.html"

    def get_object(self, queryset=None):
        return User.objects.get(id=self.request.user.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (_, vsbuser) = util.get_common_context(context, self.request, ActiveIndex.SCHEDULE.value)
        context['error_message'] = self.request.GET.get('error', "") #May be a better way of doing this?  Session objects?
        focused_event = self.request.GET.get('focused_event', "")
        if focused_event:
            try:
                context['focused_event']=vsbuser.calenderevent_set.get(pk=int(focused_event))
            except:
                pass

        event_querry_set = set()
        try:
            event_querry_set = vsbuser.get_events().all()
            context['daily_events'] = util.bucket_calenderevents(event_querry_set)
        except:
            context['daily_events'] = []

        return context

def add_schedule_item(request):
    redirect = reverse('VSB:account_schedule')
    error_message = ""
    try:
        event_name = request.POST['add_event_name']
        event_desc = request.POST['add_event_desc']
        event_time = datetime.time.fromisoformat(request.POST['add_event_time'])
        event_date = datetime.date.fromisoformat(request.POST['add_event_date'])
        f_user = User.objects.get(id=request.user.id)
        vsbuser = VSBUser.objects.get(user=f_user)
    except:
        error_message = "Please fill in the form fields."
    else:
        dt = timezone.make_aware(timezone.datetime(
            year=event_date.year, month=event_date.month, day=event_date.day, hour=event_time.hour, minute=event_time.minute
            ), timezone.get_default_timezone())

        if event_name=="":
            error_message = "Please add an event name."
        elif dt < timezone.now():
            error_message = "Events must in the future."
        else:
            same_time_set = vsbuser.calenderevent_set.filter(time__exact=dt)
            for event in same_time_set:
                if event.name == event_name:
                    error_message = "The name '" + event_name + "' already exists at that time.  Please enter another name."
                    break
    if error_message:
        redirect += "?error=" + error_message
    else:
        CalenderEvent.objects.create(user=vsbuser, time=dt, name=event_name, description=event_desc)

    return HttpResponseRedirect(redirect)

def remove_schedule_item(request, event_id):
    event = get_object_or_404(CalenderEvent, pk=event_id)
    event.delete()

    return HttpResponseRedirect(reverse('VSB:account_schedule'))
    

class AccountGroupView(generic.DetailView):
    model = User
    template_name = "VSB/account_group.html"

    def get_object(self, queryset=None):
        return self.request.user

    # def get_context_data(self, **kwargs):
    #     util.get_common_context(context, self.request, ActiveIndex.GROUPS.value)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (_, vsbuser) = util.get_common_context(context, self.request, ActiveIndex.GROUPS.value)

        context['alert'] = self.request.GET.get('alert', "")
        context['group_users'] = vsbuser.get_groupusers()
        context['invite_form'] = InviteForm
        #context['invite_form'] = InviteForm #too much info maybe?  admin level access?
        context['invites'] = []
        for invite in vsbuser.groupinvite_set.all(): #Remove any invites that you sent
            if invite.recipient == vsbuser:
                context['invites'].append(invite)

       #try:
       #     context['group_users'] = vsbuser.get_groupusers()
       #     
            # study_group_id = int(self.request.GET['studygroup_id'])
            # study_group = StudyGroup.objects.get(id=study_group_id)
            # context['study_group'] = study_group
            #context['invite_form'] = InviteForm #too much info maybe?  admin level access?
       #     context['invites'] = []
       #     for invite in vsbuser.groupinvite_set.all(): #Remove any invites that you sent
       #         if invite.recipient == vsbuser:
       #             context['invites'].append(invite)
       # except:
       #     error_message = "Internal Error" 

            
        return context


def accept_invite(request, study_group):
    group = StudyGroup.objects.get(id=study_group)
    group_invite = GroupInvite.objects.filter(study_group=group)[0]
    group_invite.accept()
    alert = "?alert=Invite accepted!"
    return HttpResponseRedirect(reverse('VSB:account_groups') + alert)

def decline_invite(request, study_group):
    group = StudyGroup.objects.get(id=study_group)
    group_invite = GroupInvite.objects.filter(study_group=group)[0]
    group_invite.decline()
    alert = "?alert=Invite declined!"
    return HttpResponseRedirect(reverse('VSB:account_groups') + alert)
    

def leave_group(request, group_id):
    f_user = User.objects.get(id=request.user.id)
    vsbuser = f_user.profile
    alert = ""
    group = StudyGroup.objects.get(id=group_id)
    if group:
        for guser in vsbuser.get_groupusers():
            if guser.study_group == group:
                alert = "?alert=Left group " + str(group.default_name)
                if len(guser.study_group.groupuser_set.all()) == 1:
                    guser.study_group.delete()
                else:
                    guser.delete()
                break
    return HttpResponseRedirect(reverse('VSB:account_groups') + alert)

def save_invite_form(request, group_id):
    f_user = User.objects.get(id=request.user.id)
    vsbuser = VSBUser.objects.get(user=f_user)
    alert = ""
    group = StudyGroup.objects.get(id=group_id)

    if group:
        for guser in vsbuser.get_groupusers():
            if guser.study_group == group:
                sender = guser

    form_type = InviteForm(request.POST)

    if form_type.is_valid():
        invite = form_type.save(commit=False)
        invite.sender = sender
        invite.study_group = group
        invite.save()
        alert = "?alert=Invite sent!"
  
    return HttpResponseRedirect(reverse('VSB:account_groups') + alert)



#Course Search Views
class CourseSearchView(generic.TemplateView):
    template_name = "VSB/course_lookup.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['logout_redirect'] = reverse('VSB:home')
        try:
            f_user = User.objects.get(id=self.request.user.id)
            vsbuser = VSBUser.objects.get(user=f_user)
        except:
            pass #Add to this
    
        #Do institutional list
        return context

class CourseSearchResultsView(generic.ListView):
    template_name = "VSB/course_lookup_results.html"
    model = VSBUser
    
    def get_queryset(self):
        f_user = User.objects.get(id=self.request.user.id)
        vsbuser = VSBUser.objects.get(user=f_user)
        query = self.request.GET.get('name')
        if not query:
            query = ""
        course_list = Course.objects.filter(name__icontains=query, institution=vsbuser.university)
        return course_list
    
    def get_object(self, queryset=None):
        return self.request.user
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (f_user, vsbuser) = util.get_common_context(context, self.request, ActiveIndex.SETTINGS.value)
        #context['form'] = MakeAccountForm
        #context['form2'] = AddCourseForm

        try:
            context['courses'] = Course.objects.all()
        except:
            pass

        return context

def add_course(request):
    f_user = User.objects.get(id=request.user.id)
    vsbuser = VSBUser.objects.get(user=f_user)

    course_to_add = Course.objects.get(id=request.GET['course_id'])
    vsbuser.add_course(course_to_add)

    alert = "?alert=Successfully added course!"

    return HttpResponseRedirect(reverse('VSB:account_settings') + alert)

def rm_course(request):
    alert = ""
    try:
        f_user = User.objects.get(id=request.user.id)
        vsbuser = VSBUser.objects.get(user=f_user)

        course_to_remove = Course.objects.get(id=request.GET['course_id'])
        vsbuser.remove_course(course_to_remove)
        alert += "?alert=Successfully removed course!"
    except:
        alert += "?alert=Error! Couldn't remove course."
    return HttpResponseRedirect(reverse('VSB:account_settings') + alert)

def add_course2(request):
    try:
        f_user = User.objects.get(id=request.user.id)
        vsbuser = VSBUser.objects.get(user=f_user)
    except:
        return HttpResponseRedirect(reverse('VSB:home')) #If the object cannot be obtained, redirect
    if request.method == "POST":
        edits = AddCourseForm(data =request.POST, instance = vsbuser)
        if edits.is_valid():
            edits.save()
            return HttpResponseRedirect(reverse("VSB:account_settings"))
    else:
        edits = MakeAccountForm(instance=f_user)
    #return render(request, 'VSB/settings.html', {'form': edits})
    return HttpResponseRedirect(reverse('VSB:account_settings'))


#Account view
class AccountView(generic.TemplateView):
    model = User
    template_name = "VSB/get_matched_form.html"

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (f_user, vsbuser) = util.get_common_context(context, self.request, ActiveIndex.MATCHED.value)
        context['alert'] = self.request.GET.get('alert', "")
        context['courses'] = vsbuser.get_courses()
        context['availability'] = (vsbuser.available_times != '[]')
        #context['misc_matching_form'] = GroupMatchingFormP2()

        return context

#Matching views
def match(request):
    course_id = request.POST.get('course_id', None)
    if course_id != '':
        course = Course.objects.get(id=int(course_id))
        if course:
            f_user = User.objects.get(id=request.user.id)
            vsbuser = VSBUser.objects.get(user=f_user)
            c_user = vsbuser.courseuser_set.get(course=course) #this is assumed to exist
            if c_user.dirty_comfort:
                return HttpResponseRedirect(reverse('VSB:account_change_comfort') + "?course_id=" + str(course_id) + 
                "&match=1")

            #remove existing sessions for this course
            for obj in MatchSession.objects.filter(vsb_user=vsbuser):
                obj.delete()

            (groups, result) = matching.generate_matching_groups(vsbuser, course, 
                util.convert_comfort_string_to_float_array(c_user.course_comfort)
            )
            create_allowed = result == matching.Scoring.ResultEnum.NO_GROUPS_FOUND or result == matching.Scoring.ResultEnum.POOR_GROUPS_FOUND

            #Extract group date (id, score, comfort score, availability score, building factor)
            groups = [(group.get_group().id, group.get_score(), group.get_helping_factor(), group.get_availability_factor(), group.get_building_factor()) for group in groups]
            session = MatchSession.create(vsbuser, groups[0:10], course, create_allowed)
            session.save() #may not be needed
            return HttpResponseRedirect(reverse('VSB:account_match_results'))
    return HttpResponseRedirect(reverse('VSB:account_settings'))

def create_matching_group(request):
    f_user = User.objects.get(id=request.user.id)
    vsbuser = VSBUser.objects.get(user=f_user)
    sessions = MatchSession.objects.filter(vsb_user=vsbuser)
    if len(sessions) > 0:
        name = request.POST.get("group_name")
        course = sessions[0].course
        if course in vsbuser.get_courses() and sessions[0].create_allowed and name:
            for group in course.studygroup_set.all():
                if name == group.default_name:
                    return HttpResponseRedirect(reverse('VSB:account_match_results') + '?error=1')
            group = StudyGroup.objects.create(course=course, default_name=name, max_users_seen=0)
            group.add_user(vsbuser)
            sessions[0].delete()
            return HttpResponseRedirect(reverse('VSB:account_groups'))
    return HttpResponseRedirect(reverse('VSB:account_matching'))

def match_join_group(request, group_id):
    f_user = User.objects.get(id=request.user.id)
    vsbuser = VSBUser.objects.get(user=f_user)
    sessions = MatchSession.objects.filter(vsb_user=vsbuser)
    if len(sessions) > 0:
        if group_id in sessions[0].get_group_ids():
            group = StudyGroup.objects.get(id=group_id)
            group.add_user(vsbuser)
            sessions[0].delete()
            return HttpResponseRedirect(reverse('VSB:account_groups'))
    return HttpResponseRedirect(reverse('VSB:account_matching'))

class MatchingView(generic.TemplateView):
    template_name = "VSB/match_results.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        (_, vsbuser) = util.get_common_context(context, self.request, ActiveIndex.MATCHED.value)

        try:
            session = MatchSession.objects.filter(vsb_user=vsbuser)[0]

            context['group_data'] = session.get_data()
            context['create_allowed'] = session.create_allowed
            context['error'] = self.request.GET.get('error', 0)
        except:
            pass #Show an error or something

        return context


#Other views
def inplace_logout(request):
    src_path = request.GET.get('src', 'admin')
    logout(request)
    return HttpResponseRedirect(src_path)

def profile_redirect(request):
    return HttpResponseRedirect(reverse('VSB:account_settings'))