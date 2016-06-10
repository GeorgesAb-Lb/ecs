from urllib.parse import urlencode
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings

class ClientCertMiddleware(object):
    def process_request(self, request):
        if not getattr(settings, 'ECS_REQUIRE_CLIENT_CERTS', True):
            return
        
        if request.user.is_authenticated():
            # nested to prevent premature imports
            url = reverse('ecs.pki.views.authenticate')
            profile = request.user.profile
            if request.path != url and \
                (profile.is_internal or profile.is_omniscient_member) and \
                not request.session.get('ecs_pki_authenticated', False):
                return HttpResponseRedirect('%s?%s' % (url, urlencode({'next': request.get_full_path()})))
        
