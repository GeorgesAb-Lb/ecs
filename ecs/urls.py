from django.conf.urls import *
from django.conf import settings
from django.contrib import admin
from django.views.static import serve
from django.shortcuts import render
from django.views.generic.base import RedirectView

from ecs.utils import forceauth

# stuff that needs called at the beginning, but not in settings.py
admin.autodiscover()

def handler500(request):
    ''' 500 error handler which includes ``request`` in the context '''
    from django.template import Context, loader
    from django.http import HttpResponseServerError

    t = loader.get_template('500.html') # You need to create a 500.html template.
    return HttpResponseServerError(t.render(Context({'request': request,})))

def fake404handler(request):
    ''' 404 error fake handler to be called via /trigger404 ''' 
    return render(request, '404.html', {}) 
    from django.template import Context, loader
    from django.http import HttpResponseNotFound

    t = loader.get_template('404.html') 
    return HttpResponseNotFound(t.render(Context({'request': request,})))
    

urlpatterns = patterns('',
    # Default redirect is same as redirect from login if no redirect is set (/dashboard/)
    url(r'^$', RedirectView.as_view(url=settings.LOGIN_REDIRECT_URL)),

    url(r'^', include('ecs.users.urls')),
    url(r'^core/', include('ecs.core.urls')),
    url(r'^checklist/', include('ecs.checklists.urls')),
    url(r'^vote/', include('ecs.votes.urls')),
    url(r'^dashboard/', include('ecs.dashboard.urls')),
    url(r'^task/', include('ecs.tasks.urls')),
    url(r'^communication/', include('ecs.communication.urls')),
    url(r'^billing/', include('ecs.billing.urls')),
    url(r'^help/', include('ecs.help.urls')),
    url(r'^boilerplate/', include('ecs.boilerplate.urls')),
    url(r'^scratchpad/', include('ecs.scratchpad.urls')),
    url(r'^document/', include('ecs.documents.urls')),
    url(r'^meeting/', include('ecs.meetings.urls')),
    url(r'^notification/', include('ecs.notifications.urls')),
    url(r'^signature/', include('ecs.signature.urls')),
    url(r'^statistics/', include('ecs.statistics.urls')),
    url(r'^', include('ecs.pki.urls')),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^static/(?P<path>.*)$', forceauth.exempt(serve), {'document_root': settings.STATIC_ROOT}),

    url(r'^search/', include('haystack.urls')),
)


if settings.DEBUG:
    from django.http import HttpResponse
    import logging
    logger = logging.getLogger(__name__)
    def __trigger_log(request):
        logger.warn('foo')
        return HttpResponse()
    urlpatterns += patterns('', 
        url(r'^debug/empty/$', lambda request: HttpResponse()),
        url(r'^debug/404/$', 'ecs.urls.fake404handler'),
        url(r'^debug/500/$', lambda request: 1/0),
        url(r'^trigger-warning-log/$', __trigger_log),
    )

if 'ecs.userswitcher' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^userswitcher/', include('ecs.userswitcher.urls')),
    )

if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^rosetta/', include('rosetta.urls')),
    )

if 'debug_toolbar' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^%s(.*)$' % "__debug__/m/", 'debug_toolbar.views.debug_media'),
    )
