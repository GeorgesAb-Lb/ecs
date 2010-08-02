from django.test import TestCase
from django.conf import settings
from celery.decorators import task

@task()
def basic_test():
    logger = self.get_logger(**kwargs)
    logger.info("celery_always eager %s" % str(settings.CELERY_ALWAYS_EAGER))
    return 'success'

class CeleryTest(TestCase):
    def test_celery(self):
        retval = basic_test.delay()
        self.failUnlessEqual(retval.get(), 'success')
        self.failUnlessEqual(retval.result, 'success')
        self.failUnless(retval.successful())

