import logging, traceback
from functools import wraps

import httpagentparser
from django.conf import settings

__all__ = ['UA']

BROWSER_SUPPORT_OK = 1
BROWSER_SUPPORT_NO = 2
BROWSER_SUPPORT_TMP_NO = 3
BROWSER_SUPPORT_CRAWLER = 4

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG if settings.DEBUG else logging.INFO)

class Version(tuple):
    def __new__(cls, version_str):
        version = []
        if version_str:
            for bit in version_str.split('.'):
                try:
                    bit = int(bit)
                except ValueError:
                    pass
                version.append(bit)
        else:
            version = [0,]
        instance = super(Version, cls).__new__(cls, version)
        return instance

    def __cmp__(self, other):
        if isinstance(other, basestring):
            other = Version(other)
        for i in xrange(len(other)):
            if self[i] > other[i]:
                return +1
            elif self[i] < other[i]:
                return -1
        return 0

def parse_ua(fn):
    @wraps(fn)
    def _inner(ua_str):
        ua = httpagentparser.detect(ua_str)
        for x in ('browser', 'platform', 'flavor'):
            if x in ua and 'version' in ua[x]:
                ua[x]['version'] = Version(ua[x]['version'])
        return fn(ua)
    return _inner

def supported_starting(name, version, tmp_unsupported=None):
    version = Version(version)
    tmp_unsupported = tmp_unsupported or []

    @parse_ua
    def _fn(ua):
        b = ua['browser']
        if not b:
            return
        if b['name'] == name:
            if any(b['version'] == v for v in tmp_unsupported):
                return BROWSER_SUPPORT_TMP_NO
            if b['version'] >= version:
                return BROWSER_SUPPORT_OK
            else:
                return BROWSER_SUPPORT_NO
    return _fn

@parse_ua
def android_quirks(ua):
    b = ua['browser']
    if not b:
        return
    if b['name'] == 'AndroidBrowser':
        platform = ua['platform']
        if platform and platform['name'] == 'Android' and platform['version'] >= '3.2':
            return BROWSER_SUPPORT_OK

def crawler_quirks(ua_str):
    ua_str = ua_str.lower()
    bots = ('googlebot', 'yahoo! slurp', 'msnbot', 'bingbot')

    if any(bot in ua_str for bot in bots):
        return BROWSER_SUPPORT_CRAWLER

# browser filtering rules; order is significant
BROWSER_FILTER_RULES = (
    supported_starting('Firefox', '4'),
    supported_starting('Chrome', '10'),
    android_quirks,
    supported_starting('Safari', '5'),
    supported_starting('Microsoft Internet Explorer', '10'),
    crawler_quirks,
)

class UA(object):
    def __init__(self, ua_str):
        self.support = None
        for rule_fn in BROWSER_FILTER_RULES:
            try:
                support = rule_fn(ua_str)
                if not support is None:
                    self.support = support
                    break
            except Exception as e:
                logger.info('parsing UA string threw an exception\nUA string: %s\n%s', ua_str, traceback.format_exc())

    is_supported = property(lambda self: self.support == BROWSER_SUPPORT_OK)
    is_unsupported = property(lambda self: self.support == BROWSER_SUPPORT_NO)
    is_tmp_unsupported = property(lambda self: self.support == BROWSER_SUPPORT_TMP_NO)
    is_crawler = property(lambda self: self.support == BROWSER_SUPPORT_CRAWLER)
