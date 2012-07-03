from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404

from ecs.utils.viewutils import render, JSONResponse
from ecs.users.utils import user_flag_required
from ecs.boilerplate.models import Text
from ecs.boilerplate.forms import TextForm
from ecs.utils.security import readonly


@readonly()
@user_flag_required('is_internal')
def list_boilerplate(request):
    return render(request, 'boilerplate/list.html', {
        'texts': Text.objects.order_by('slug'),
    })
    

@user_flag_required('is_internal')
def edit_boilerplate(request, text_pk=None):
    if text_pk is None:
        text = None
    else:
        text = get_object_or_404(Text, pk=text_pk)
    
    form = TextForm(request.POST or None, instance=text)
    if form.is_valid():
        text = form.save(commit=False)
        text.author = request.user
        text.save()
        return HttpResponseRedirect(reverse('ecs.boilerplate.views.list_boilerplate'))
    
    return render(request, 'boilerplate/form.html', {
        'text': text,
        'form': form,
    })


@user_flag_required('is_internal')
def delete_boilerplate(request, text_pk=None):
    text = get_object_or_404(Text, pk=text_pk)
    text.delete()
    return HttpResponseRedirect(reverse('ecs.boilerplate.views.list_boilerplate'))
    

@readonly()
@user_flag_required('is_internal')
def select_boilerplate(request):
    texts = Text.objects.all()
    if 'q' in request.GET:
        texts = texts.filter(slug__icontains=request.GET['q'].strip())
    return JSONResponse(list(texts.values('slug', 'text')))
