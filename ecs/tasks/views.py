import random
from functools import reduce

from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import Http404, QueryDict
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.views.decorators.http import require_POST

from ecs.utils.viewutils import redirect_to_next_url
from ecs.users.utils import user_flag_required, sudo
from ecs.core.models import Submission
from ecs.core.models.constants import (
    SUBMISSION_LANE_BOARD, SUBMISSION_LANE_EXPEDITED,
    SUBMISSION_LANE_RETROSPECTIVE_THESIS, SUBMISSION_LANE_LOCALEC,
)
from ecs.checklists.models import Checklist
from ecs.tasks.models import Task
from ecs.tasks.forms import TaskListFilterForm
from ecs.tasks.signals import task_declined
from ecs.tasks.tasks import send_delete_message
from ecs.votes.models import Vote
from ecs.notifications.models import NOTIFICATION_MODELS, Notification
from ecs.meetings.models import Meeting


@user_flag_required('is_internal')
def task_backlog(request, submission_pk=None):
    submission = get_object_or_404(Submission, pk=submission_pk)
    with sudo():
        tasks = list(
            Task.objects.for_submission(submission)
                .select_related('task_type', 'task_type__group', 'assigned_to',
                    'assigned_to__profile', 'medical_category')
                .order_by('created_at')
        )

    return render(request, 'tasks/log.html', {
        'tasks': tasks,
        'submission': submission,
    })


@user_flag_required('is_internal')
def delete_task(request, submission_pk=None, task_pk=None):
    submission = get_object_or_404(Submission, pk=submission_pk)
    with sudo():
        task = get_object_or_404(Task.objects.for_submission(submission).open(),
            pk=task_pk, task_type__is_dynamic=True)
        task.mark_deleted()
    if task.task_type.is_dynamic and task.created_by and \
        task.created_by != request.user:
        send_delete_message(task, request.user)
    return redirect('ecs.tasks.views.task_backlog', submission_pk=submission_pk)


def my_tasks(request, template='tasks/compact_list.html', submission_pk=None, ignore_task_types=True):
    submission = None
    all_tasks = (Task.objects.for_user(request.user).for_widget().open()
        .select_related('task_type', 'task_type__workflow_node')
        .order_by('task_type__workflow_node__uid', 'created_at', 'assigned_at'))

    if submission_pk:
        submission = get_object_or_404(Submission, pk=submission_pk)
        all_tasks = all_tasks.for_submission(submission)
    else:
        usersettings = request.user.ecs_settings

        filterdict = request.POST or request.GET or None
        if filterdict is None and usersettings.task_filter is not None:
            filterdict = QueryDict(usersettings.task_filter)
        filterform = TaskListFilterForm(filterdict)

        if request.method == 'POST':
            usersettings.task_filter = filterform.urlencode()
            usersettings.save()
            if len(request.GET) > 0:
                return redirect(request.path)

    open_tasks = all_tasks.filter(assigned_to=None).for_submissions(
        Submission.objects.exclude(biased_board_members=request.user))

    my_tasks = all_tasks.filter(assigned_to=request.user)

    proxy_tasks = (all_tasks
        .for_submissions(
            Submission.objects.exclude(biased_board_members=request.user))
        .filter(assigned_to__profile__is_indisposed=True))

    if not submission and filterform.is_valid():
        cd = filterform.cleaned_data
        past_meetings = cd['past_meetings']
        next_meeting = cd['next_meeting']
        upcoming_meetings = cd['upcoming_meetings']
        no_meeting = cd['no_meeting']
        lane_board = cd['lane_board']
        lane_expedited = cd['lane_expedited']
        lane_retrospective_thesis = cd['lane_retrospective_thesis']
        lane_localec = cd['lane_localec']
        lane_none = cd['lane_none']
        amg = cd['amg']
        mpg = cd['mpg']
        thesis = cd['thesis']
        other = cd['other']

        if (past_meetings and next_meeting and upcoming_meetings and no_meeting and
            lane_board and lane_expedited and lane_retrospective_thesis and lane_localec and lane_none and
            amg and mpg and thesis and other):
            pass
        else:
            submissions = Submission.objects.all()

            if not (past_meetings and next_meeting and upcoming_meetings and no_meeting):
                qs = []
                if past_meetings:
                    qs.append(Q(meetings__ended__isnull=False))
                if next_meeting:
                    try:
                        meeting = Meeting.objects.next()
                    except Meeting.DoesNotExist:
                        pass
                    else:
                        qs.append(Q(meetings=meeting))
                if upcoming_meetings:
                    qs.append(Q(meetings__isnull=False, meetings__ended=None))
                if no_meeting:
                    qs.append(Q(meetings=None))

                if qs:
                    submissions = submissions.filter(reduce(lambda x, y: x | y, qs))
                else:
                    submissions = submissions.none()

            if not (lane_board and lane_expedited and lane_retrospective_thesis and lane_localec and lane_none):
                lanes = []
                if lane_board:
                    lanes.append(SUBMISSION_LANE_BOARD)
                if lane_expedited:
                    lanes.append(SUBMISSION_LANE_EXPEDITED)
                if lane_retrospective_thesis:
                    lanes.append(SUBMISSION_LANE_RETROSPECTIVE_THESIS)
                if lane_localec:
                    lanes.append(SUBMISSION_LANE_LOCALEC)
                q = Q(workflow_lane__in=lanes)
                if lane_none:
                    q |= Q(workflow_lane=None)

                submissions = submissions.filter(q)

            if not (amg and mpg and thesis and other):
                amg_q = Submission.objects.amg()
                mpg_q = Submission.objects.mpg()
                thesis_q = Submission.objects.exclude(
                    current_submission_form__project_type_education_context=None)
                other_q = Submission.objects.exclude(
                    pk__in=(amg_q | mpg_q | thesis_q).values('pk'))

                q = Submission.objects.none()
                if amg:
                    q |= amg_q
                if mpg:
                    q |= mpg_q
                if thesis:
                    q |= thesis_q
                if other:
                    q |= other_q
                submissions &= q

            submission_q = submissions.values('pk')
            checklist_ct = ContentType.objects.get_for_model(Checklist)
            submission_ct = ContentType.objects.get_for_model(Submission)
            vote_ct = ContentType.objects.get_for_model(Vote)
            notification_cts = list(map(ContentType.objects.get_for_model, NOTIFICATION_MODELS))

            submission_tasks_q = Q(
                content_type=submission_ct, data_id__in=submission_q)

            checklist_tasks_q = Q(
                content_type=checklist_ct,
                data_id__in=Checklist.objects.filter(
                    submission__in=submission_q
                ).values('pk'))

            vote_tasks_q = Q(
                content_type=vote_ct,
                data_id__in=Vote.objects.filter(
                    submission_form__submission__in=submission_q
                ).values('pk'))

            notification_tasks_q = Q(
                content_type__in=notification_cts,
                data_id__in=Notification.objects.filter(
                    submission_forms__submission__in=submission_q
                ).values('pk'))

            open_tasks = open_tasks.filter(submission_tasks_q |
                checklist_tasks_q | vote_tasks_q | notification_tasks_q)
    
        if not ignore_task_types:
            task_types = filterform.cleaned_data['task_types']
            if task_types:
                open_tasks = open_tasks.filter(task_type__workflow_node__uid__in=
                    task_types.values('workflow_node__uid'))

    data = {
        'submission': submission,
        'form_id': 'task_list_filter_%s' % random.randint(1000000, 9999999),
        'my_tasks': my_tasks,
        'proxy_tasks': proxy_tasks,
        'open_tasks': open_tasks,
    }
    if not submission:
        data.update({
            'filterform': filterform,
            'bookmarklink':
                '{0}?{1}'.format(
                    request.build_absolute_uri(request.path),
                    filterform.urlencode()
                ),
        })

    return render(request, template, data)


def task_list(request, **kwargs):
    kwargs.setdefault('template', 'tasks/list.html')
    kwargs.setdefault('ignore_task_types', False)
    return my_tasks(request, **kwargs)


@require_POST
def accept_task(request, task_pk=None, full=False):
    task = get_object_or_404(Task.objects.acceptable_for_user(request.user), pk=task_pk)
    task.accept(request.user)

    submission_pk = request.GET.get('submission')
    view = 'ecs.tasks.views.task_list' if full else 'ecs.tasks.views.my_tasks'
    return redirect_to_next_url(request, reverse(view, kwargs={'submission_pk': submission_pk} if submission_pk else None))

@require_POST
def accept_task_full(request, task_pk=None):
    return accept_task(request, task_pk=task_pk, full=True)

@require_POST
def accept_tasks(request, full=False):
    task_ids = request.POST.getlist('task_id')
    submission_pk = request.GET.get('submission')
    tasks = Task.objects.acceptable_for_user(request.user).filter(id__in=task_ids)

    for task in tasks:
        task.accept(request.user)

    view = 'ecs.tasks.views.task_list' if full else 'ecs.tasks.views.my_tasks'
    return redirect_to_next_url(request, reverse(view, kwargs={'submission_pk': submission_pk} if submission_pk else None))

@require_POST
def accept_tasks_full(request):
    return accept_tasks(request, full=True)

@require_POST
def decline_task(request, task_pk=None, full=False):
    task = get_object_or_404(Task.objects, assigned_to=request.user,
        task_type__is_delegatable=True, pk=task_pk)
    task.assign(None)
    task_declined.send(type(task.node_controller), task=task)

    submission_pk = request.GET.get('submission')
    view = 'ecs.tasks.views.task_list' if full else 'ecs.tasks.views.my_tasks'
    return redirect_to_next_url(request, reverse(view, kwargs={'submission_pk': submission_pk} if submission_pk else None))

@require_POST
def decline_task_full(request, task_pk=None):
    return decline_task(request, task_pk=task_pk, full=True)


def reopen_task(request, task_pk=None):
    task = get_object_or_404(Task, pk=task_pk)
    if task.workflow_token.workflow.is_finished:
        raise Http404()
    if not task.node_controller.is_repeatable():
        raise Http404()
    new_task = task.reopen(user=request.user)
    return redirect(new_task.url)

def do_task(request, task_pk=None):
    task = get_object_or_404(Task, assigned_to=request.user, pk=task_pk)
    url = task.url
    if not task.closed_at is None:
        url = task.afterlife_url
        if url is None:
            raise Http404()
    return redirect(url)
