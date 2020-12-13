from django.http import HttpResponseRedirect

def default_path(response):
    """
    Redirects the user to the default app.
    Default app:  VSB
    """
    return HttpResponseRedirect("VSB/")