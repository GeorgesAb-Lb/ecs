# Django settings for ecs project.

import os.path, platform

PROJECT_DIR = os.path.dirname(__file__)

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)
MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'    # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = os.path.join(PROJECT_DIR, 'ecs.db')  # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# celery configuration
BROKER_HOST = 'localhost'
BROKER_PORT = 5672
BROKER_USER = 'ecsuser'
BROKER_PASSWORD = 'ecspassword'
BROKER_VHOST = 'ecshost'
CELERY_RESULT_BACKEND = 'amqp'  # we have to use amqp, because of the test cases
CELERY_IMPORTS = (
    'ecs.core.tests.task_queue',
    'ecs.core.task_queue',
)

# Default is DEBUG, but eg. platform.node ecsdev.ep3.at user testecs overrides that
# (because we want 404 and 500 custom errors and log the error)
DEBUG = True
TEMPLATE_DEBUG = DEBUG

# use postgres if on host ecsdev.ep3.at depending username
if platform.node() == "ecsdev.ep3.at":
    import getpass
    user = getpass.getuser()
    DBPWD_DICT = {}
    assert user in DBPWD_DICT, " ".join(("did not find",user,"in DBPWD_DICT"))

    DATABASE_ENGINE = 'postgresql_psycopg2'
    DATABASE_HOST = '127.0.0.1'
    DEFAULT_FROM_EMAIL = 'noreply@ecsdev.ep3.at'
    DATABASE_NAME = user
    DATABASE_USER = user
    DATABASE_PASSWORD = DBPWD_DICT[user]
    
    # rabbit mq users and db users are the same (also passwords)
    BROKER_USER = user
    BROKER_PASSWORD = DBPWD_DICT[user]
    BROKER_VHOST = user
    
    if user == "testecs":
        DEBUG = False
        TEMPLATE_DEBUG = False
else:
    try:
        from local_settings import *
    except ImportError:
        pass

# get version of the Programm from version.py if exists (gets updated on deployment)
try:
    from version import *
except ImportError:
    ECS_VERSION = 'unknown'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Vienna'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'de-AT'

# this should be default, but to be sure
DEFAULT_CHARSET = "utf-8"
FILE_CHARSET = "utf-8"

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'ptn5xj+85fvd=d4u@i1-($z*otufbvlk%x1vflb&!5k94f$i3w'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth", # FIXME: replace with "django.contrib.auth.context_processors.auth" for django 1.2 
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'ecs.utils.forceauth.ForceAuth',
    'ecs.groupchooser.middleware.GroupChooserMiddleware',
    'djangodblog.middleware.DBLogMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    'reversion.middleware.RevisionMiddleware',
)   

# debug toolbar config:
# middleware on bottom:
#    'debug_toolbar.middleware.DebugToolbarMiddleware',
# application anyware:
#    'debug_toolbar',
DEBUG_TOOLBAR_CONFIG = {"INTERCEPT_REDIRECTS": False}
INTERNAL_IPS = ('127.0.0.1','78.46.72.166', '78.46.72.189', '78.46.72.188', '78.46.72.187')

ROOT_URLCONF = 'ecs.urls'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_DIR, 'templates'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django_extensions',

    'django.contrib.admin',
    'django.contrib.admindocs',

    'south',
    'django_nose',
    'reversion',
    'djangodblog',
    'celery',
    'ecs.utils.countries',

    'ecs.core',
    'ecs.utils',
    'ecs.feedback',
    'ecs.docstash',
    'ecs.groupchooser',
    'ecs.pdfviewer',
    #'ecs.workflow',
    #'ecs.tasks',
)

# django-db-log
# temporary for testing, cat 404 defaults to false
DBLOG_CATCH_404_ERRORS = True

# filestore is now in root dir (one below source)
FILESTORE = os.path.realpath(os.path.join(PROJECT_DIR, "..", "..", "ecs-store"))

# use django-nose as default test runner
TEST_RUNNER = 'django_nose.run_tests'

# FIXME: clarify which part of the program works with this setting
FIXTURE_DIRS = [os.path.join(PROJECT_DIR, "fixtures")]
