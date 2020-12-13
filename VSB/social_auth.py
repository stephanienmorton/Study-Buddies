from django.contrib.auth.models import User
#import groupy
#from groupy import Client
from .models import VSBUser

def process_new_user(backend, user, response, *args, **kwargs):
    vsb_user = VSBUser.objects.filter(user=user).first() #There can be only one
    if vsb_user is None:
        VSBUser.objects.create(user=user)
   
        