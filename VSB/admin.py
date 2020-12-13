from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import CalenderEvent, VSBUser, Course, Institution, StudyGroup, GroupUser, CourseUser, MatchSession, GroupInvite, GroupMeIntegration

# Maybe don't let admins change these values.
'''
class VSBUserInline(admin.StackedInline):
    model = VSBUser
    can_delete = False

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (VSBUserInline, )

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
'''

class EventInlineAdmin(admin.TabularInline):
    model = CalenderEvent
    extra = 1

"""
class VSBUserAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields':['institution', 'courses', 'image', 'display_name', 'utc_timezone_delta']})
    ]

    inlines = [EventInlineAdmin]
    list_display = ['user']
"""

admin.site.register(VSBUser)
#admin.site.register(VSBUser, VSBUserAdmin)
admin.site.register(Course)
admin.site.register(Institution)
admin.site.register(StudyGroup)
admin.site.register(GroupUser)
admin.site.register(CourseUser)
admin.site.register(MatchSession)
admin.site.register(CalenderEvent)
admin.site.register(GroupInvite)
admin.site.register(GroupMeIntegration)