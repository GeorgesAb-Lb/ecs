import random

from django.shortcuts import get_object_or_404

from ecs.utils.viewutils import render
from ecs.scratchpad.forms import ScratchPadForm
from ecs.scratchpad.models import ScratchPad, SCRATCHPAD_FORTUNES
from ecs.core.models.submissions import Submission

def popup(request, scratchpad_pk=None):
    submission = None
    submission_pk = request.GET.get('submission')
    if submission_pk:
        submission = get_object_or_404(Submission, pk=submission_pk)

    if scratchpad_pk:
        scratchpad = get_object_or_404(ScratchPad, owner=request.user, pk=scratchpad_pk)
        submission = scratchpad.submission
    else:
        scratchpad, created = ScratchPad.objects.get_or_create(owner=request.user, submission=submission, defaults={'text': random.choice(SCRATCHPAD_FORTUNES)})

    form = ScratchPadForm(request.POST or None, instance=scratchpad)
    if request.method == 'POST' and form.is_valid():
        form.save()

    return render(request, 'scratchpad/popup.html', {
        'form': form,
        'scratchpad': scratchpad,
        'submission': submission,
    })

def popup_list(request):
    scratchpads = ScratchPad.objects.filter(owner=request.user).order_by('-modified_at')[:100]
    return render(request, 'scratchpad/popup_list.html', {
        'scratchpads': scratchpads,
    })