import tempfile
import os

from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.conf import settings

from ecs.utils.viewutils import render, redirect_to_next_url
from ecs.users.utils import user_group_required

from ecs.pki.utils import get_ca, get_subject_for_user
from ecs.pki.forms import CertForm
from ecs.pki.models import Certificate


@user_group_required('EC-Signing Group')
def cert_list(request, user_pk=None):
    return render(request, 'pki/cert_list.html', {
        'certs': Certificate.objects.select_related('user').order_by('is_revoked', 'user__email', 'cn'),
    })


@user_group_required('EC-Signing Group')
def create_cert(request, user_pk=None):
    form = CertForm(request.POST or None)

    if form.is_valid():
        ca = get_ca()
        cn = form.cleaned_data.get('cn').strip()
        user = form.cleaned_data['user']
        subject = get_subject_for_user(user, cn=cn)
        fd, tmp = tempfile.mkstemp()
        try:
            fingerprint = ca.make_cert(subject, tmp, passphrase=form.cleaned_data['passphrase'])
            with open(tmp, 'r') as f:
                pkcs12 = f.read()
        finally:
            os.remove(tmp)

        Certificate.objects.create(user=user, cn=cn, subject=subject, fingerprint=fingerprint)
        response = HttpResponse(pkcs12, content_type='application/x-pkcs12')
        response['Content-Disposition'] = 'attachment;filename=%s.p12' % fingerprint.replace(':', '-')
        return response
        
    return render(request, 'pki/create_cert.html', {
        'form': form,
    })


@require_POST
@user_group_required('EC-Signing Group')
def revoke_cert(request, cert_pk=None):
    cert = get_object_or_404(Certificate, pk=cert_pk)
    ca = get_ca()
    ca.revoke_by_fingerprint(cert.fingerprint)
    cert.is_revoked = True
    cert.save()
    return HttpResponseRedirect(reverse('ecs.pki.views.cert_list'))


def authenticate(request):
    if request.user.ecs_profile.is_internal or getattr(settings, 'ECS_MANDATORY_CLIENT_CERTS', False):
        request.session['ecs_pki_authenticated'] = True
        request.session.modified = True
    return redirect_to_next_url(request, reverse('ecs.dashboard.views.view_dashboard'))
    
