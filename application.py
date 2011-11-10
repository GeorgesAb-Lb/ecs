# ecs main application environment config
import platform
import sys
import os
import shutil
import tempfile
import subprocess
import distutils.dir_util

from deployment.utils import get_pythonenv, import_from, get_pythonexe, zipball_create, write_template,\
    write_regex_replace
from deployment.pkgmanager import get_pkg_manager, package_merge, packageline_split
from ecs.target import SetupTarget
import logging


# packages
##########

# packages needed for the application
main_packages = """

# postgresql database bindings
psycopg2:req:apt:apt-get:libpq-dev
psycopg2:req:mac:homebrew:postgresql
psycopg2:req:mac:macports:postgresql84-server
psycopg2:req:suse:zypper:postgresql-devel
psycopg2:req:openbsd:pkg:postgresql-server
psycopg2:req:openbsd:pkg:postgresql-client
psycopg2:inst:!win:pypi:psycopg2
psycopg2:instbin:win:http://www.stickpeople.com/projects/python/win-psycopg/psycopg2-2.0.13.win32-py2.6-pg8.4.1-release.exe

# sqlite database bindings
pysqlite:req:apt:apt-get:libsqlite3-dev
pysqlite:req:mac:homebrew:sqlite
pysqlite:req:mac:macports:sqlite3
pysqlite:req:suse:zypper:sqlite3-devel
pysqlite:req:openbsd:pkg:sqlite3
pysqlite:inst:!win:pypi:pysqlite
pysqlite:instbin:win:http://pysqlite.googlecode.com/files/pysqlite-2.5.6.win32-py2.6.exe

# timezone handling
pytz:inst:all:pypi:pytz
# python docutils, needed by django, ecs, and others
roman:inst:all:pypi:roman
docutils:inst:all:pypi:docutils\>=0.7


# django main
django:inst:all:pypi:django==1.2.3
south:inst:all:pypi:south
django-piston:inst:all:http://bitbucket.org/jespern/django-piston/get/default.gz
django-extensions:inst:all:http://github.com/django-extensions/django-extensions/tarball/master
# docstash now uses django-picklefield
django-picklefield:inst:all:pypi:django-picklefield
# Todo: django-dbtemplates version 1.2.1 has many new features (reversion support, south support, better caching support)
django-dbtemplates:inst:all:pypi:django-dbtemplates
# django caching uses memcache if available
python-memcached:inst:all:pypi:python-memcached

# preprocessing, combining, compressing of js and css 
#lxml could be used by django_compressor, but we use HtmlParser
#lxml:req:apt:apt-get:libxslt1-dev,libxml2-dev
#lxml:inst:!win:pypi:lxml\<2.3
#lxml:instbin:win:http://pypi.python.org/packages/2.6/l/lxml/lxml-2.2.8.win32-py2.6.exe
cssmin:inst:all:pypi:cssmin
django-appconf:inst:all:pypi:django-appconf\>=0.4.1
versiontools:inst:all:pypi:versiontools
django_compressor:inst:all:pypi:django_compressor\>=1.1
# sass/scss css preprocessor
pyscss:inst:all:pypi:pyScss\>=1.0.8


# pdf parsing/cleaning: origami
ruby:req:apt:apt-get:ruby
rubygems:req:apt:apt-get:rubygems
ruby:req:win:http://rubyforge.org/frs/download.php/75107/rubyinstaller-1.8.7-p352.exe:exec:ruby.exe
#origami:static:all:http://rubygems.org/gems/origami-1.2.3.gem:custom:pdfcop


# unit testing
nose:inst:all:pypi:nose
django-nose:inst:all:pypi:django-nose
# for testing the export we need concurrent requests
django_concurrent_test_server:inst:all:pypi:django_concurrent_test_server
# for manage.py test_windmill we need windmill
windmill:inst:all:pypi:windmill\>=1.6
# for random text generation in windmill tests
cicero:inst:all:pypi:cicero
"""

# importlib is a dependency of celery, but importlib is included in
# Python 2.7 and newer for 2.x
v = platform.python_version_tuple()
if not (int(v[0]) == 2 and int(v[1]) >= 7):
    main_packages += "importlib:inst:all:pypi:importlib\n"

main_packages += """
# queuing: celery 
python-dateutil:inst:all:pypi:python-dateutil\<2.0.0
anyjson:inst:all:pypi:anyjson\>=0.3.1
# Fixme: new set would be amqplib 1.0.2, kombu 1.4.1, celery 2.3.3 
#amqplib:inst:all:pypi:amqplib==0.6.1
amqplib:inst:all:pypi:amqplib\>=1.0.2
#kombu:inst:all:pypi:kombu==1.1.6
kombu:inst:all:pypi:kombu\>=1.4.1
pyparsing:inst:all:pypi:pyparsing\<2.0.0
#celery:inst:all:pypi:celery==2.2.6
celery:inst:all:pypi:celery==2.3.3
django-picklefield:inst:all:pypi:django-picklefield
#django-celery:inst:all:pypi:django-celery==2.2.4
django-celery:inst:all:pypi:django-celery==2.3.3


# mail: ecsmail, communication: lamson mail server
chardet:inst:all:pypi:chardet
jinja2:inst:all:pypi:jinja2
lockfile:inst:all:pypi:lockfile
mock:inst:all:pypi:mock\<0.8
# we dont use python-daemon functionality in lamson, but lamson.utils imports daemon and fails
# so we fake it for windows and right now also for the rest, was python-daemon:inst:!win:pypi:python-daemon==1.5.5
python-daemon:inst:all:dir:ecs/utils/fake-daemon/
lamson:inst:all:pypi:lamson
beautifulsoup:inst:all:pypi:beautifulsoup\<3.1
beautifulcleaner:inst:all:http://github.com/downloads/enki/beautifulcleaner/BeautifulCleaner-2.0dev.tar.gz


# ecs/signature: tomcat, mocca and pdf-as
# needed for crossplatform patch support (we patch pdf-as.war for preview of signed pdf)
python-patch:static:all:http://python-patch.googlecode.com/files/patch-11.01.py:copy:python-patch.py
# for apt (ubuntu/debian) systems, tomcat 6 is used as a user installation
tomcat:req:apt:apt-get:tomcat6-user
tomcat_apt_user:static:apt:file:dummy:custom:None
# for all others, a custom downloaded tomcat 6 is used
tomcat_other_user:static:!apt:http://mirror.sti2.at/apache/tomcat/tomcat-6/v6.0.33/bin/apache-tomcat-6.0.33.tar.gz:custom:apache-tomcat-6.0.33
pdfas:static:all:http://egovlabs.gv.at/frs/download.php/276/pdf-as-3.2-webapp.zip:custom:pdf-as.war
mocca:static:all:http://egovlabs.gv.at/frs/download.php/312/BKUOnline-1.3.6.war:custom:BKUOnline-1.3.6.war


# ecs/mediaserver: file encryption, used for storage vault 
gnupg:req:apt:apt-get:gnupg
gnupg:req:mac:macports:gnupg
gnupg:req:mac:homebrew:gnupg
gnupg:req:suse:zypper:gpg2
gnupg:req:openbsd:pkg:gnupg
gnupg:req:win:ftp://ftp.gnupg.org/gcrypt/binary/gnupg-w32cli-1.4.10b.exe:exec:gpg.exe


# search
whoosh:inst:all:pypi:whoosh\>=2.2.2
# pysolr uses beautiful soup optional for solr error support
# pysolr uses httplib2 with fallback to httplib
httplib2:inst:all:pypi:httplib2
# we use == for pysolr because we dont want 2.1beta
pysolr:inst:all:pypi:pysolr==2.0.15
ordereddict:inst:all:pypi:ordereddict
django-haystack:inst:all:pypi:django-haystack\>=1.2.5
# pdf text extract
pdftotext:req:apt:apt-get:poppler-utils
#pdftotext:req:mac:homebrew:poppler
pdftotext:req:mac:macports:poppler
pdftotext:req:suse:zypper:poppler-tools
pdftotext:req:openbsd:pkg:poppler
pdftotext:req:openbsd:pkg:poppler-data
pdftotext:static:win:http://gd.tuwien.ac.at/publishing/xpdf/xpdf-3.02pl4-win32.zip:unzipflat:pdftotext.exe

# excel generation / xlwt
xlwt:inst:all:pypi:xlwt


# webkit html to pdf
wkhtmltopdf:static64:apt|suse:http://wkhtmltopdf.googlecode.com/files/wkhtmltopdf-0.10.0_rc2-static-amd64.tar.bz2:tar:wkhtmltopdf-amd64
wkhtmltopdf:static32:apt|suse:http://wkhtmltopdf.googlecode.com/files/wkhtmltopdf-0.10.0_rc2-static-i386.tar.bz2:tar:wkhtmltopdf-i386
wkhtmltopdf:static:mac:http://wkhtmltopdf.googlecode.com/files/wkhtmltopdf-OSX-0.10.0_rc2-static.tar.bz2:tar:wkhtmltopdf
wkhtmltopdf:req:win:http://wkhtmltopdf.googlecode.com/files/wkhtmltox-0.10.0_rc2-installer.exe:exec:wkhtmltopdf.exe

# (ecs/utils/pdfutils): pdf validation (is_valid, pages_nr)
pdfminer:inst:all:pypi:pdfminer


# mediaserver image generation
# ############################

# pdf manipulation, barcode stamping
pdftk:req:apt:apt-get:pdftk
pdftk:static:win:http://www.pdfhacks.com/pdftk/pdftk-1.41.exe.zip:unzipflat:pdftk.exe
# Available in: http://packman.mirrors.skynet.be/pub/packman/suse/11.3/Packman.repo
pdftk:req:suse:zypper:pdftk
# Mac OS X: get pdftk here: http://www.pdflabs.com/docs/install-pdftk/
#pdftk:req:mac:dmg:http://fredericiana.com/downloads/pdftk1.41_OSX10.6.dmg
# OpenBSD: build pdftk yourself: http://www.pdflabs.com/docs/build-pdftk/

# mediaserver: python-memcached (and mockcache for testing) 
python-memcached:inst:all:pypi:python-memcached
mockcache:inst:all:pypi:mockcache

# mediaserver: needs ghostscript for rendering
ghostscript:req:apt:apt-get:ghostscript
#ghostscript:req:mac:homebrew:ghostscript
ghostscript:req:mac:macports:ghostscript
ghostscript:req:suse:zypper:ghostscript-library
ghostscript:req:openbsd:pkg:ghostscript--
ghostscript:req:win:http://ghostscript.com/releases/gs871w32.exe:exec:gswin32c.exe

# mediaserver: new rendering may use mupdf
mupdf:static32:apt|suse:http://mupdf.com/download/mupdf-0.9-linux-i386.tar.gz:tarflat:pdfdraw
mupdf:static64:apt|suse:http://mupdf.com/download/mupdf-0.9-linux-amd64.tar.gz:tarflat:pdfdraw
mupdf:static:win:http://mupdf.com/download/mupdf-0.9-windows.zip:unzipflat:pdfdraw
#mupdf 0.8.165 if currently not available for mac, last available is 0.7
mupdf:static:mac:http://mupdf.com/download/archive/mupdf-0.7-darwin-i386.tar.gz:tarflat:pdfdraw

# mediaserver: image magick is used for rendering tasks as well
imagemagick:req:apt:apt-get:imagemagick
#imagemagick:req:mac:homebrew:imagemagick
imagemagick:req:mac:macports:imagemagick
imagemagick:req:suse:zypper:ImageMagick
imagemagick:req:openbsd:pkg:ImageMagick--
# we check for montage.exe because on windows convert.exe exists already ... :-(
imagemagick:static:win:ftp://ftp.imagemagick.org/pub/ImageMagick/binaries/ImageMagick-6.6.5-Q16-windows.zip:unzipflatsecond:montage.exe

# PIL requirements for ubuntu
libjpeg62-dev:req:apt:apt-get:libjpeg62-dev
zlib1g-dev:req:apt:apt-get:zlib1g-dev
libfreetype6-dev:req:apt:apt-get:libfreetype6-dev
liblcms1-dev-devel:req:apt:apt-get:liblcms1-dev
# PIL requirements for opensuse
libjpeg62-devel:req:suse:zypper:libjpeg62-devel
zlib-devel:req:suse:zypper:zlib
freetype2-devel:req:suse:zypper:freetype2-devel
liblcms1:req:suse:zypper:liblcms1

python-pil:inst:!win:pypi:PIL
python-pil:instbin:win:http://effbot.org/media/downloads/PIL-1.1.7.win32-py2.6.exe

# deployment: manage.py massimport
antiword:req:apt:apt-get:antiword
antiword:req:mac:homebrew:antiword
antiword:req:mac:macports:antiword
# antiword has to be built by hand for opensuse
#antiword:req:suse:zypper:antiword
antiword:req:openbsd:pkg:antiword
antiword:static:win:http://www.informatik.uni-frankfurt.de/~markus/antiword/antiword-0_37-windows.zip:unzipflat:antiword.exe
# antiword is needed for ecs/core/management/massimport.py (were we load word-doc-type submission documents into the database)
beautifulsoup:inst:all:pypi:beautifulsoup\<3.1
# mpmath needed for massimport statistic function
mpmath:inst:all:pypi:mpmath

# feedback: jsonrpclib for ecs feedback and fab ticket
jsonrpclib:inst:all:file:externals/joshmarshall-jsonrpclib-283a2a9-ssl_patched.tar.gz


# logging: django-sentry; 
# uuid:inst:all:pypi:uuid uuid is in mainlibs since 2.3 ... and was not thread safe in 2.5...
django-templatetag-sugar:inst:all:pypi:django-templatetag-sugar
django-indexer:inst:all:pypi:django-indexer\>=0.3.0
django-paging:inst:all:pypi:django-paging\>=0.2.4
pygooglechart:inst:all:pypi:pygooglechart
django-sentry:inst:all:pypi:django-sentry==1.11.4

# ecs.help needs reversion from now on
django-reversion:inst:all:pypi:django-reversion

# diff_match_patch is used for the submission diff and django-reversion
diff_match_patch:inst:all:http://github.com/pinax/diff-match-patch/tarball/master

# django-rosetta is used only for doc.ecsdev.ep3.at , but we keep it in the main requirements for now
django-rosetta:inst:all:pypi:django-rosetta
"""

# packages that are needed to run guitests using windmill, not strictly needed, except you do guitesting
guitest_packages = """
windmill:inst:all:pypi:windmill\>=1.6
# for random text generation in windmill tests
cicero:inst:all:pypi:cicero
# Firefox and a vncserver is needed for headless gui testing
firefox:req:apt:apt-get:firefox
vncserver:req:apt:apt-get:vnc4server
"""


# software quality testing packages, not strictly needed, except you do coverage analysis
quality_packages= """
# nose and django-nose is in main app
unittest-xml-reporting:inst:all:pypi:unittest-xml-reporting
coverage:inst:!win:pypi:coverage\<3.4
coverage:instbin:win:http://pypi.python.org/packages/2.6/c/coverage/coverage-3.2.win32-py2.6.exe
nose-xcover:inst:all:http://github.com/cmheisel/nose-xcover/tarball/master
unittest2:inst:all:pypi:unittest2
logilab-common:inst:all:pypi:logilab-common\>=0.49.0
logilab-astng:inst:all:pypi:logilab-astng\>=0.20.0
pylint:inst:all:pypi:pylint
#django-lint:inst:all:http://chris-lamb.co.uk/releases/django-lint/LATEST/django-lint-0.13.tar.gz

# django-test-utils is used for testmaker
beautifulsoup:inst:all:pypi:beautifulsoup\<3.1
django-test-utils:inst:all:pypi:django-test-utils
"""


# packages needed or nice to have for development
developer_packages=  """
# windows needed for manage.py makemessages and compilemessages
#http://ftp.gnome.org/pub/gnome/binaries/win32/dependencies/gettext-runtime_0.18.1.1-2_win32.zip
#http://ftp.gnome.org/pub/gnome/binaries/win32/dependencies/gettext-tools_0.18.1.1-2_win32.zip

# debugging toolbar, switched back to robhudson original tree
django-debug-toolbar:inst:all:http://github.com/robhudson/django-debug-toolbar/tarball/master
#django-debug-toolbar:inst:all:http://github.com/dcramer/django-debug-toolbar/tarball/master

# support for django-devserver
guppy:inst:!win:pypi:guppy
guppy:instbin:win:http://pypi.python.org/packages/2.6/g/guppy/guppy-0.1.9.win32-py2.6.exe
sqlparse:inst:all:pypi:sqlparse
werkzeug:inst:all:pypi:werkzeug
django-devserver:inst:all:https://github.com/dcramer/django-devserver/tarball/master

# cherrypy running django (threaded wsgi server)
django-wsgiserver:inst:all:pypi:django-wsgiserver

# interactive python makes your life easier
ipython:inst:win:pypi:pyreadline
ipython:inst:all:pypi:ipython

# dependency generation for python programs
sfood:inst:all:pypi:snakefood

# FIXME: who needs simplejson, and why is it in developer packages
simplejson:inst:all:pypi:simplejson
# deployment: massimport statistics 
levenshtein:inst:!win:http://pylevenshtein.googlecode.com/files/python-Levenshtein-0.10.1.tar.bz2
"""

# required for django_extensions unittests:
#pycrypto:inst:all:pypi:pycrypto>=2.0
#pyasn1:inst:all:pypi:pyasn1
#keyczar:inst:all:http://keyczar.googlecode.com/files/python-keyczar-0.6b.061709.tar.gz
# maybe interesting: fudge:inst:all:pypi:fudge


# packages needed for full production rollout (eg. VM Rollout)
system_packages = """
# apache via modwsgi is used to serve the main app
apache2:req:apt:apt-get:apache2-mpm-prefork
modwsgi:req:apt:apt-get:libapache2-mod-wsgi

# postgresql is used as primary database
postgresql:req:apt:apt-get:postgresql

# exim is used as incoming smtp firewall and as smartmx for outgoing mails
exim:req:apt:apt-get:exim4

# solr is used for fulltext indexing
solr-jetty:req:apt:apt-get:solr-jetty

# rabbitmq is used as AMPQ Broker in production
rabbitmq-server:req:apt:apt-get:rabbitmq-server
#rabbitmq-server:req:mac:macports:rabbitmq-server
# available here: http://www.rabbitmq.com/releases/rabbitmq-server/v2.1.0/rabbitmq-server-2.1.0-1.suse.noarch.rpm
# uncomment is if there is a possibility to specify repositories for suse
#rabbitmq-server:req:suse:zypper:rabbitmq-server

# Memcached is used for django caching, and the mediaserver uses memcached for its docshot caching
memcached:req:apt:apt-get:memcached
#memcached:req:mac:macports:memcached
#memcached:req:suse:zypper:memcached
#memcached:req:win:http://splinedancer.com/memcached-win32/memcached-1.2.4-Win32-Preview-20080309_bin.zip:unzipflatroot:memcached.exe
# btw, we only need debian packages in the system_packages, but it doesnt hurt to fillin for others 
"""


def custom_check_tomcat_apt_user(pkgline, checkfilename):
    print "custom_check_tomcat_apt_user"
    return False

def custom_install_tomcat_apt_user(pkgline, filename):
    print "custom_install_tomcat_apt_user: not active"
    return True

def custom_check_tomcat_other_user(pkgline, checkfilename):
    return os.path.exists(os.path.join(get_pythonenv(), "tomcat-6"))
    
def custom_install_tomcat_other_user(pkgline, filename):
    (name, pkgtype, platform, resource, url, behavior, checkfilename) = packageline_split(pkgline)
    pkg_manager = get_pkg_manager()
    temp_dir = tempfile.mkdtemp()
    temp_dest = os.path.join(temp_dir, checkfilename)
    final_dest = os.path.join(get_pythonenv(), "tomcat-6")
    result = False
    
    try:
        if os.path.exists(final_dest):
            shutil.rmtree(final_dest)
        if pkg_manager.static_install_tar(filename, temp_dir, checkfilename, pkgline):
            write_regex_replace(os.path.join(temp_dest, 'conf', 'server.xml'),
                r'([ \t])+(<Connector port=)("[0-9]+")([ ]+protocol="HTTP/1.1")',
                r'\1\2"4780"\4')
            shutil.copytree(temp_dest, final_dest)
            result = True
    finally:    
        shutil.rmtree(temp_dir)
    
    return result

def custom_check_pdfas(pkgline, checkfilename):
    return os.path.exists(os.path.join(get_pythonenv(), "tomcat-6", "webapps", checkfilename))
   
def _patch_pdfas_war(target):
    patchlib = import_from(os.path.join(os.path.dirname(get_pythonexe()), 'python-patch.py'))
    patchlib.logger.setLevel(logging.INFO)
    old_cwd = os.getcwd()
    temp_dir = tempfile.mkdtemp()
    pkg_manager = get_pkg_manager()
    success = False
    
    try:
        if pkg_manager.static_install_unzip(target, temp_dir, None, None):
            os.chdir(os.path.join(temp_dir, "jsp"))
            p = patchlib.fromfile(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                'signature', 'pdf-as-3.2-jsp.patch'))
            if p.apply():
                os.remove(target)
                zipball_create(target, temp_dir)
                success = True
            else:
                print("Error: Failed patching:", target, temp_dir)
    finally:
        os.chdir(old_cwd)
        shutil.rmtree(temp_dir)
        
    return success

def custom_install_pdfas(pkgline, filename):
    (name, pkgtype, platform, resource, url, behavior, checkfilename) = packageline_split(pkgline)
    pkg_manager = get_pkg_manager()
    temp_dir = tempfile.mkdtemp()
    temp_dest = os.path.join(temp_dir, "tomcat-6")
    final_dest = os.path.join(get_pythonenv(), "tomcat-6")
    result = False
    
    try:
        if pkg_manager.static_install_unzip(filename, temp_dir, checkfilename, pkgline):
            if _patch_pdfas_war(os.path.join(temp_dest, "webapps", checkfilename)):
                write_regex_replace(
                    os.path.join(temp_dest, 'conf', 'pdf-as', 'cfg', 'config.properties'),
                    r'(moc.sign.url=)(http://127.0.0.1:8080)(/bkuonline/http-security-layer-request)',
                    r'\1http://localhost:4780\3')
                write_regex_replace(
                    os.path.join(temp_dest, 'conf', 'pdf-as', 'cfg', 'pdf-as-web.properties'),
                    r'([#]?)(retrieve_signature_data_url_override=)(http://localhost:8080)(/pdf-as/RetrieveSignatureData)',
                    r'\2http://localhost:4780\4')
                
                distutils.dir_util.copy_tree(temp_dest, final_dest, verbose=True)
                result = True
    finally:    
        shutil.rmtree(temp_dir)
    
    return result

def custom_check_mocca(pkgline, checkfilename):
    return os.path.exists(os.path.join(get_pythonenv(), "tomcat-6", "webapps", checkfilename))

def custom_install_mocca(pkgline, filename):
    (name, pkgtype, platform, resource, url, behavior, checkfilename) = packageline_split(pkgline)
    outputdir = os.path.join(get_pythonenv(), "tomcat-6", "webapps")
    pkg_manager = get_pkg_manager()
    return pkg_manager.static_install_copy(filename, outputdir, checkfilename, pkgline)

def custom_install_origami(pkgline, filename):
    return custom_install_ruby_gem(pkgline, filename)

def custom_install_ruby_gem(pkgline, filename):
    
    gem_home = os.path.join(get_pythonenv(),'gems')
    filename_dir = os.path.dirname(filename)
    filename = os.path.basename(filename)
    
    if not os.path.exists(gem_home):
        os.mkdir(gem_home)
        
    if not os.path.exists(os.path.join(filename_dir, filename)):
        print "gem to install does not exist:", filename
    
    if sys.platform == 'win32':
        gem_home = gem_home.replace("\\", "/")
        bin_dir = os.path.join(os.environ['VIRTUAL_ENV'],'Scripts').replace("\\", "/")
        install = 'cd {0}& set GEM_HOME="{1}"& set GEM_PATH="{1}"&\
gem install --no-ri --no-rdoc --local --bindir="{2}" {3}'.format(
            filename_dir, gem_home, bin_dir, filename)
    else:
        bin_dir = os.path.join(os.environ['VIRTUAL_ENV'],'bin')
        install = 'export GEM_HOME="{0}"; export GEM_PATH="{0}";\
gem install --no-ri --no-rdoc --local --bindir="{1}" {2}'.format(
            filename_dir, gem_home, bin_dir, filename)
    
    popen = subprocess.Popen(install, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=True)
    stdout, stderr = popen.communicate() 
    returncode = popen.returncode  
    if returncode != 0:
        print "Error:", returncode, stdout, stderr
        return False
    else:
        return True
 

# target bundles
################

testing_bundle = main_packages
default_bundle = main_packages
future_bundle = main_packages
developer_bundle = package_merge((default_bundle, quality_packages, guitest_packages, developer_packages))
quality_bundle = package_merge((default_bundle, quality_packages))
system_bundle = package_merge((default_bundle, system_packages))

package_bundles = {
    'default': default_bundle,
    'testing': testing_bundle,
    'future': future_bundle,

    'developer': developer_bundle,
    'quality': quality_bundle,
    'qualityaddon': quality_packages,
    'guitestaddon': guitest_packages,
    'developeraddon': developer_packages,
    'system': system_bundle,
}

logrotate_targets = {
    'default': '*.log'
}

upstart_targets = {
    'celeryd': (None, './manage.py celeryd -l warning -L ../../ecs-log/celeryd.log'),    
    'celerybeat': (None, './manage.py celerybeat -S djcelery.schedulers.DatabaseScheduler -l warning -L ../../ecs-log/celerybeat.log'),
    'ecsmail': (None, './manage.py ecsmail server ../../ecs-log/ecsmail.log'), 
    'signing': ('upstart-tomcat.conf', ''),
}

test_flavors = {
    'default': './manage.py test',
    'windmill': './manage.py test_windmill firefox integration',
    'mainapp': './manage.py test',
    'mediaserver': 'false',  # include in the mainapp tests
    'mailserver': 'false', # included in the mainapp tests
}


# app commands
##############

def help():
    print ''' ecs-main application
Usage: fab app:ecs,command[,options]

commands:
         
  * wmrun(browser, targettest, *args, **kwargs):
    run windmill tests; Usage: fab app:ecs,wmrun,<browser>,targettest[,*args,[targethost=<url>]]
  
  * wmshell(browser="firefox", *args, **kwargs):    
    run windmill shell; Usage: fab app:ecs,wmshell,[<browser=firefox>[,*args,[targethost=<url>]]] 

target support:

  * update(*args, **kwargs):
    calls SetupTarget.update(*arg,**kwargs), defaults to sane Methodlist
    Example: fab target:ecs,update,daemonsstop,source_update
    
    Use: "fab target:ecs,help" for usage

    '''

def system_setup(use_sudo=True, dry=False, hostname=None, ip=None):
    s = SetupTarget(use_sudo= use_sudo, dry= dry, hostname= hostname, ip= ip)
    s.system_setup()

def _wm_helper(browser, command, targettest, targethost, *args):
    from deployment.utils import fabdir
    # FIXME it seems without a PYTHON_PATH set we cant import from ecs...
    sys.path.append(fabdir())
    from ecs.integration.windmillsupport import windmill_run
    return windmill_run(browser, command, targettest, targethost, *args)
    
def wmrun(browser, targettest, *args, **kwargs):
    """ run windmill tests; Usage: fab app:ecs,wmrun,<browser>,targettest[,*args,[targethost=<url>]] """
    print "args", args
    print "kwargs", kwargs
    targethost = kwargs["targethost"] if "targethost" in kwargs else "http://localhost:8000" 
    _wm_helper(browser, "run", targettest, targethost, *args)
    
def wmshell(browser="firefox", *args, **kwargs):    
    """ run windmill shell; Usage: fab app:ecs,wmshell,[<browser=firefox>[,*args,[targethost=<url>]]] """ 
    targethost = kwargs["targethost"] if "targethost" in kwargs else "http://localhost:8000"
    _wm_helper(browser, "shell", None, targethost, *args)
