from copy import deepcopy
from collections import OrderedDict

from django.utils.translation import ugettext as _

from ecs.billing.models import Price, STUDY_PRICING_OTHER, \
    STUDY_PRICING_MULTICENTRIC_AMG_MAIN, STUDY_PRICING_MULTICENTRIC_AMG_LOCAL, \
    STUDY_PRICING_REMISSION


SUBMISSION_STAT_TEMPLATE = OrderedDict((
    ('local', {
        'label': _('fees note - local EC'),
        'price': STUDY_PRICING_MULTICENTRIC_AMG_LOCAL,
        'count': 0,
    }),
    ('amg', {
        'label': _('fees note - AMG'),
        'price': STUDY_PRICING_OTHER,
        'count': 0,
    }),
    ('mpg', {
        'label': _('fees note - MPG'),
        'price': STUDY_PRICING_OTHER,
        'count': 0,
    }),
    ('other', {
        'label': _('fees note - other'),
        'price': STUDY_PRICING_OTHER,
        'count': 0,
    }),
    ('main_monocentric', {
        'label': _('fees note - controlling-EC monocentric'),
        'price': STUDY_PRICING_OTHER,
        'count': 0,
    }),
    ('main_multicentric', {
        'label': _('fees note - controlling-EC multicentric'),
        'price': STUDY_PRICING_MULTICENTRIC_AMG_MAIN,
        'count': 0,
    }),
    ('remission', {
        'label': _('fees note - remission'),
        'price': STUDY_PRICING_REMISSION,
        'count': 0,
    }),
))

AMG_KEYS = {
    # (multicentric, main)
    (True, True): 'main_multicentric',
    (False, True): 'main_monocentric',
    (False, False): 'amg',
    (True, False): 'local',
}

def collect_submission_billing_stats(submission_list):
    summary = deepcopy(SUBMISSION_STAT_TEMPLATE)
    total = 0
    for submission in submission_list:
        if submission.remission:
            key = 'remission'
        elif submission.current_submission_form.is_amg:
            key = AMG_KEYS[(submission.is_multicentric, getattr(submission.main_ethics_commission, 'system', False))]
        elif submission.current_submission_form.is_mpg:
            key = 'mpg'
        else:
            key = 'other'
        summary[key]['count'] += 1
        price = Price.objects.get_for_submission(submission)
        total += price.price

    for val in summary.values():
        val['price'] = Price.objects.get(category=val['price'])

    return {'summary': summary, 'total': total}