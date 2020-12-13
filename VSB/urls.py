from django.urls import path, re_path, reverse, reverse_lazy
from django.contrib.auth.decorators import login_required

from . import views

GLOBAL_LOGIN_URL = reverse_lazy('social:begin', args=['google-oauth2'])

app_name = "VSB"
urlpatterns = [
    path('', views.profile_redirect, name='home'), 
    re_path(r'^logout/$', views.inplace_logout, name='logout'),
    path('profile', views.profile_redirect, name='account'),
    path('profile/groups/send_invite/<int:group_id>/', login_required(views.save_invite_form, login_url=GLOBAL_LOGIN_URL), name='send_invite'),
    re_path(r'^profile/groups/token', login_required(views.token, login_url=GLOBAL_LOGIN_URL), name='token'),
    path('profile/groups/groupme/<int:group_id>/', login_required(views.authenticate, login_url=GLOBAL_LOGIN_URL), name='groupme'),
    # path('profile/groups/messages/<int:group_id>/', login_required(views.messages, login_url=GLOBAL_LOGIN_URL), name='messages'),
    path('profile/groups/link/<int:group_id>/', login_required(views.groupme_link, login_url=GLOBAL_LOGIN_URL), name='link'),
    re_path(r'^profile/change', login_required(views.save_changes, login_url=GLOBAL_LOGIN_URL), name='change'),
    re_path(r'^profile/settings/comfort/save', login_required(views.save_comfort, login_url=GLOBAL_LOGIN_URL), name='account_change_comfort_save'),
    re_path(r'^profile/settings/comfort/$', login_required(views.AccountComfortView.as_view(), login_url=GLOBAL_LOGIN_URL), name='account_change_comfort'),
    re_path(r'^profile/settings/$', login_required(views.AccountSettingsView.as_view(), login_url=GLOBAL_LOGIN_URL), name='account_settings'),
    re_path(r'^profile/getmatched/run/$', login_required(views.match, login_url=GLOBAL_LOGIN_URL), name='account_match_run'),
    path('profile/getmatched/join/<int:group_id>', login_required(views.match_join_group, login_url=GLOBAL_LOGIN_URL), name='match_join_group'),
    path('profile/getmatched/create', login_required(views.create_matching_group, login_url=GLOBAL_LOGIN_URL), name='match_create_group'),
    path('profile/getmatched/results', login_required(views.MatchingView.as_view(), login_url=GLOBAL_LOGIN_URL), name='account_match_results'),
    re_path(r'^profile/getmatched', login_required(views.AccountView.as_view(), login_url=GLOBAL_LOGIN_URL), name='account_matching'),
    #path('ajax/load-topics/', views.load_topics, name='ajax_load_topics'),
    #re_path(r'^profile/getmatched2', login_required(views.AccountView2.as_view(), login_url=GLOBAL_LOGIN_URL), name='account_matching2'),
    path('profile/groups/invite/<int:study_group>/', login_required(views.accept_invite, login_url=GLOBAL_LOGIN_URL), name='accept_invite'),
    path('profile/groups/decline/<int:study_group>/', login_required(views.decline_invite, login_url=GLOBAL_LOGIN_URL), name='decline_invite'),
    path('profile/groups/leave/<int:group_id>/', login_required(views.leave_group, login_url=GLOBAL_LOGIN_URL), name='leave_group'),
    path('profile/addcourse', login_required(views.add_course2, login_url=GLOBAL_LOGIN_URL), name='add_course2'),
    re_path(r'^profile/groups/$', login_required(views.AccountGroupView.as_view(), login_url=GLOBAL_LOGIN_URL), name='account_groups'),
    re_path(r'^profile/schedule/additem', login_required(views.add_schedule_item, login_url=GLOBAL_LOGIN_URL), name='account_schedule_additem'),
    path('profile/schedule/removeitem/<int:event_id>/', login_required(views.remove_schedule_item, login_url=GLOBAL_LOGIN_URL), name='account_schedule_removeitem'),
    re_path(r'^profile/schedule/$', login_required(views.AccountScheduleView.as_view(), login_url=GLOBAL_LOGIN_URL), name='account_schedule'),
    re_path(r'^profile/courselookup/', login_required(views.CourseSearchView.as_view(), login_url=GLOBAL_LOGIN_URL), name='course_lookup'),
    path('courselookup/results/', login_required(views.CourseSearchResultsView.as_view(), login_url=GLOBAL_LOGIN_URL), name='course_lookup_results'),
    re_path(r'^courselookup/addclass/', login_required(views.add_course, login_url=GLOBAL_LOGIN_URL), name='add_course'),
    re_path(r'^courselookup/rmclass/$', login_required(views.rm_course, login_url=GLOBAL_LOGIN_URL), name='rm_course'),
    re_path(r'^profile/addcourse', login_required(views.add_course2, login_url=GLOBAL_LOGIN_URL), name='add_course2'),

] 
