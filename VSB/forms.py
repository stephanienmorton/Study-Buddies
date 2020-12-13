from django import forms
from django.utils.translation import gettext_lazy as _

from .models import User, VSBUser, Course, GroupInvite, Institution
from . import util

COMFORT_LEVELS = (
    ("1", "1"),
    ("2", "2"),
    ("3", "3"),
    ("4", "4"),
    ("5", "5"),
)       

TOPICS = (
    ("1", "Assignments"),
    ("2", "Exam Prep"),
    ("3", "General Studying"),
)



WEEKDAYS = (
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
    ("Saturday", "Saturday"),
    ("Sunday", "Sunday"),
)       


TIMES = (
    ("0", "12 am"),
    ("1","1 am"),
    ("2","2 am"),
    ("3","3 am"),
    ("4","4 am"),
    ("5","5 am"),
    ("6","6 am"),
    ("7"," 7 am"),
    ("8", "8 am"),
    ("9", "9 am"),
    ("10", "10 am"),
    ("11", "11 am"),
    ("12", "12 pm"),
    ("13", "1 pm"),
    ("14", "2 pm"),
    ("15", "3 pm"),
    ("16", "4 pm"),
    ("17", "5 pm"),
    ("18", "6 pm"),
    ("19", "7 pm"),
    ("20", "8 pm"),
    ("21", "9 pm"),
    ("22", "10 pm"),
    ("23","11 pm"),
)

class MakeAccountForm(forms.ModelForm):
    class Meta:
        model = VSBUser
        fields = ('display_name', 'preferred_email', 'image', )
        widgets = {
            'display_name': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50', 'placeholder' : 'Display Name'}),
            'preferred_email': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '50', 'placeholder' : 'Email'}),
        }
        
class InstitutionForm(forms.ModelForm):
    class Meta:
        model = VSBUser
        fields = ('university',)
       
      

class ClassForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name',]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '80', 'placeholder' : "Search...(eg: CS1110)"}),
        }


class TimeZoneAvailability(forms.Form):
    OPTIONS = util.TIME_ZONE_CHOICES
    category = forms.ChoiceField(label='category', choices=util.TIME_ZONE_CHOICES )
        
class DateAvaliabilityForm(forms.Form):
    weekday_selection = forms.ChoiceField(label='Week', choices=WEEKDAYS)
    time_selection = forms.ChoiceField(label='Time', choices=TIMES)
   
        
class AddCourseForm(forms.ModelForm):
    courses = forms.ModelMultipleChoiceField(queryset=Course.objects.all())


class InviteForm(forms.ModelForm):
    class Meta:
        model = GroupInvite
        fields = {'recipient'}


      
        

    
        
    

        
    

        