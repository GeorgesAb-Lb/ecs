from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin
from django.views.static import serve
from django.views.generic.simple import direct_to_template, redirect_to
from django.core.urlresolvers import reverse
from ecs.utils import forceauth
from ecs import workflow
import django

# stuff that needs called at the beginning, but not in settings.py

admin.autodiscover()
workflow.autodiscover()

import logging
from sentry.client.handlers import SentryHandler
logging.getLogger().addHandler(SentryHandler())

# Add StreamHandler to sentry's default so you can catch missed exceptions
logger = logging.getLogger('sentry.errors')
logger.propagate = False
logger.addHandler(logging.StreamHandler())

# patch the user __unicode__ method, so the hash in the username field does not show up
def _patch_user_unicode():
    from django.contrib.auth.models import User
    from ecs.users.utils import get_full_name

    User.__unicode__ = get_full_name

_patch_user_unicode()


urlpatterns = patterns('',
    # Default redirect is same as redirect from login if no redirect is set (/dashboard/)
    url(r'^$', 'django.views.generic.simple.redirect_to', {'url': settings.LOGIN_REDIRECT_URL}),

    url(r'^audit/', include('ecs.audit.urls')),
    url(r'^core/', include('ecs.core.urls')),
    url(r'^dashboard/', include('ecs.dashboard.urls')),
    url(r'^fastlane/', include('ecs.fastlane.urls')),

    url(r'^feedback/', include('ecs.feedback.urls')),
    url(r'^userswitcher/', include('ecs.userswitcher.urls')),
    url(r'^pdfviewer/', include('ecs.pdfviewer.urls')),
    url(r'^mediaserver/', include('ecs.mediaserver.urls')),
    url(r'^tasks/', include('ecs.tasks.urls')),
    url(r'^communication/', include('ecs.communication.urls')),
    url(r'^billing/', include('ecs.billing.urls')),
    url(r'^help/', include('ecs.help.urls')),
    url(r'^boilerplate/', include('ecs.boilerplate.urls')),
    url(r'^', include('ecs.users.urls')),
    url(r'^', include('ecs.documents.urls')),
    url(r'^', include('ecs.meetings.urls')),
    url(r'^', include('ecs.notifications.urls')),

    url(r'^bugshot/', include('ecs.bugshot.urls')),
    url(r'^search/', include('haystack.urls')),
    url(r'^i18n/', include('django.conf.urls.i18n')),

    url(r'^static/(?P<path>.*)$', forceauth.exempt(serve), {'document_root': settings.MEDIA_ROOT}),

    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    
    #url(r'^test/', direct_to_template, {'template': 'test.html'}),
    #url(r'^tests/killableprocess/$', 'ecs.utils.tests.killableprocess.timeout_view'),
    url(r'^trigger500/$', lambda request: 1/0), 
)

if 'sentry' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        # redirect sentry login/logout pages to standard pages because we dont want sentry handle login
        #url(r'^sentry/login$', 'django.views.generic.simple.redirect_to', {'url': reverse("ecs.users.views.login")}),
        #url(r'^sentry/logout$', 'django.views.generic.simple.redirect_to', {'url': reverse("ecs.users.views.logout")}),
        url(r'^sentry/', include('sentry.urls')),
    )
    
if 'rosetta' in settings.INSTALLED_APPS:
    urlpatterns += patterns('',
        url(r'^rosetta/', include('rosetta.urls')),
    )

if 'debug_toolbar' in settings.INSTALLED_APPS:
    # XXX: this should be set by the debug middleware, but it doesnt work, so we hack it here
    urlpatterns += patterns('',
        url(r'^%s(.*)$' % "__debug__/m/", 'debug_toolbar.views.debug_media'),
    )

