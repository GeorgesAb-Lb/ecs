# -*- coding: utf-8 -*-
from functools import wraps

from django.template import loader
from django.conf import settings

from ecs.communication.models import Thread
from ecs.users.utils import get_user, get_current_user


def msg_fun(func):
    @wraps(func)
    def _inner(sender, receiver, *args, **kwargs):
        # import here to prevent circular imports
        from ecs.tasks.models import Task
        from ecs.core.models import Submission

        submission = kwargs.get('submission', None)
        task = kwargs.get('task', None)
        if isinstance(sender, basestring):
            sender = get_user(sender)
        if isinstance(receiver, basestring):
            receiver = get_user(receiver)
        kwargs['submission'] = Submission.objects.get(pk=int(submission)) if isinstance(submission, (basestring, int)) else submission
        kwargs['task'] = Task.objects.get(pk=int(task)) if isinstance(task, (basestring, int)) else task

        args = [sender, receiver] + list(args)
        return func(*args, **kwargs)

    return _inner

@msg_fun
def send_message(sender, receiver, subject, text, submission=None, task=None, reply_receiver=None):
    thread = Thread.objects.create(
        subject=subject,
        sender=sender, 
        receiver=receiver,
        submission=submission,
        task=task,
    )
    message = thread.add_message(sender, text=text, reply_receiver=reply_receiver)
    return thread

def send_system_message(*args, **kwargs):
    kwargs.setdefault('reply_receiver', get_current_user())
    return send_message(get_user('root@system.local'), *args, **kwargs)

@msg_fun
def send_message_template(sender, receiver, subject, template, context, *args, **kwargs):
    request = kwargs.get('request')
    if context is None:
        context = {}
    else:
        context = context.copy()

    context.setdefault('sender', sender)
    context.setdefault('receiver', receiver)
    context.setdefault('submission', kwargs.get('submission'))
    context.setdefault('task', kwargs.get('task'))
    context.setdefault('ABSOLUTE_URL_PREFIX', settings.ABSOLUTE_URL_PREFIX)

    if isinstance(template, (tuple, list)):
        template = loader.select_template(template)
    if not hasattr(template, 'render'):
        template = loader.get_template(template)

    text = template.render(context, request)

    return send_message(sender, receiver, subject, text, *args, **kwargs)

def send_system_message_template(*args, **kwargs):
    kwargs.setdefault('reply_receiver', get_current_user())
    return send_message_template(get_user('root@system.local'), *args, **kwargs)
