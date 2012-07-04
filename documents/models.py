# -*- coding: utf-8 -*-

import hashlib
import os
import tempfile
import datetime
import mimetypes
import logging
from uuid import uuid4
from contextlib import contextmanager
from shutil import copyfileobj

from django.db import models
from django.db.models.signals import post_save, post_delete
from django.core.files.storage import FileSystemStorage
from django.core.files import File
from django.utils.encoding import smart_str
from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import slugify
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext

from ecs.authorization import AuthorizationManager
from ecs.users.utils import get_current_user
from ecs.mediaserver.client import generate_media_url, generate_pages_urllist, download_from_mediaserver


logger = logging.getLogger(__name__)


class DocumentPersonalization(models.Model):
    id = models.SlugField(max_length=36, primary_key=True, default=lambda: uuid4().get_hex())
    document = models.ForeignKey('Document', db_index=True)
    user = models.ForeignKey(User, db_index=True)

    objects = AuthorizationManager()

    def __unicode__(self):
        return "%s - %s - %s - %s" % (self.id, str(self.document), self.document.get_filename(), self.user.get_full_name())


class DocumentType(models.Model):
    name = models.CharField(max_length=100)
    identifier = models.CharField(max_length=30, db_index=True, blank=True, default= "")
    helptext = models.TextField(blank=True, default="")
    is_hidden = models.BooleanField(default=False)
    is_downloadable = models.BooleanField(default=True)

    def __unicode__(self):
        return ugettext(self.name)


def incoming_document_to(instance=None, filename=None):
    instance.original_file_name = os.path.basename(os.path.normpath(filename)) # save original_file_name
    _, file_ext = os.path.splitext(filename)
    target_name = os.path.normpath(os.path.join(settings.INCOMING_FILESTORE, instance.uuid + file_ext[:5]))
    return target_name
    
class DocumentFileStorage(FileSystemStorage):
    def get_available_name(self, name):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        Limit the length to some reasonable value.
        """
        dir_name, file_name = os.path.split(name)
        file_root, file_ext = os.path.splitext(file_name)
        # If the filename already exists, add _ with a 4 digit number till we get an empty slot.
        counter = 0
        while self.exists(name):
            # file_ext includes the dot.
            counter += 1
            name = os.path.join(dir_name, "%s_%04d%s" % (file_root, counter, file_ext))
        return name

    def path(self, name):
        # We need to overwrite the default behavior, because django won't let us save documents outside of MEDIA_ROOT
        return smart_str(os.path.normpath(name))


class DocumentManager(AuthorizationManager): 
    def create_from_buffer(self, buf, **kwargs): 
        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmpname = tmp.name
        tmp.write(buf)
        tmp.flush()
        tmp.seek(0)
        
        if 'doctype' in kwargs and isinstance(kwargs['doctype'], basestring):
            kwargs['doctype'] = DocumentType.objects.get(identifier=kwargs['doctype'])

        kwargs.setdefault('date', datetime.datetime.now())
        doc = self.create(file=File(open(tmpname,'rb')), **kwargs)
        tmp.close()
        return doc


C_BRANDING_CHOICES = (
    ('b', 'brand id'),
    ('p', 'personalize'),
    ('n', 'never brand'),
)

C_STATUS_CHOICES = (
    ('new', _('new')),
    ('uploading', _('uploading')),
    ('uploaded', _('uploaded')),
    ('indexing', _('indexing')),
    ('indexed', _('indexed')),
    ('prime', _('prime')),
    ('ready', _('ready')),
    ('aborted', _('aborted')),
    ('deleted', _('deleted')),
)

class Document(models.Model):
    uuid = models.SlugField(max_length=36, unique=True)
    hash = models.SlugField(max_length=32)
    original_file_name = models.CharField(max_length=250, null=True, blank=True)
    mimetype = models.CharField(max_length=100, default='application/pdf')
    pages = models.IntegerField(null=True, blank=True)
    branding = models.CharField(max_length=1, default='b', choices=C_BRANDING_CHOICES)
    allow_download = models.BooleanField(default=True)
    status = models.CharField(max_length=15, default='new', choices=C_STATUS_CHOICES)
    retries = models.IntegerField(default=0, editable=False)

    # user supplied data
    file = models.FileField(null=True, upload_to=incoming_document_to, storage=DocumentFileStorage(), max_length=250)
    name = models.CharField(max_length=250)
    doctype = models.ForeignKey(DocumentType)
    version = models.CharField(max_length=250)
    date = models.DateTimeField()
    replaces_document = models.ForeignKey('Document', null=True, blank=True)
    
    # relation to a object
    content_type = models.ForeignKey(ContentType, null=True)
    object_id = models.PositiveIntegerField(null=True)
    parent_object = GenericForeignKey('content_type', 'object_id')
    
    objects = DocumentManager()
    
    @property
    def doctype_name(self):
        if self.doctype_id:
            return _(self.doctype.name)
        return u"Sonstige Unterlagen"
    
    def __unicode__(self):
        t = "Sonstige Unterlagen"
        if self.doctype_id:
            t = self.doctype.name
        return u'{0} {1}-{2} vom {3}'.format(t, self.name, self.version, self.date.strftime('%d.%m.%Y'))

    def get_filename(self):
        if self.mimetype == 'application/vnd.ms-excel': # HACK: we want .xls not .xlb for excel files
            ext = '.xls'
        else:
            ext = mimetypes.guess_extension(self.mimetype) or '.bin'
        name_slices = [self.doctype.name if self.doctype else 'Unterlage', self.name, self.version, self.date.strftime('%Y.%m.%d')]
        if self.parent_object and hasattr(self.parent_object, 'get_filename_slice'):
            name_slices.insert(0, self.parent_object.get_filename_slice())
        name = slugify('-'.join(name_slices))
        return ''.join([name, ext])
    
    def get_downloadurl(self):
        if (not self.allow_download) or (self.branding not in [c[0] for c in C_BRANDING_CHOICES]):
            return None
    
        if self.mimetype != 'application/pdf' or self.branding == 'n':
            personalization = None
            brand = False
        else:
            personalization = self.add_personalization(get_current_user()).id if self.branding == 'p' else None
            brand = self.branding in ('p', 'b')

        return generate_media_url(self.uuid, self.get_filename(), mimetype=self.mimetype, personalization=personalization, brand=brand)

    def get_from_mediaserver(self):
        ''' load actual data from mediaserver including optional branding ; you rarely use this. '''
        personalization = self.add_personalization(get_current_user()).id if self.branding == 'p' else None
        brand = self.branding in ('p', 'b')
        return download_from_mediaserver(self.uuid, self.get_filename(), personalization=personalization, brand=brand)
    
    @contextmanager
    def as_temporary_file(self):
        with tempfile.NamedTemporaryFile() as tmp:
            copyfileobj(self.get_from_mediaserver(), tmp)
            tmp.seek(0)
            yield tmp

    def get_pages_list(self): 
        ''' returns a list of ('description', 'access-url', 'page', 'tx', 'ty', 'width', 'height') pictures
        for every supported rendersize options for every page of the document
        '''
        return generate_pages_urllist(self.uuid, self.pages)
               
    def get_personalizations(self, user=None):
        ''' Get a list of (id, user) tuples of personalizations for this document, or None if none exist '''
        return None
        
    def add_personalization(self, user):
        ''' Add unique id connected to a user and document download ''' 
        return False

    def save(self, **kwargs):
        #print("uuid: {0}, mimetype: {1}, status: {2}, retries: {3}".format(self.uuid, self.mimetype, self.status, self.retries))

        if not self.uuid: 
            self.uuid = uuid4().get_hex() # generate a new random uuid
            content_type = None
            if self.file.name or self.original_file_name:
                filename_to_check = self.file.name if self.file.name else self.original_file_name
                content_type, encoding = mimetypes.guess_type(filename_to_check) # look what kind of mimetype we would guess

        if not self.hash:
            m = hashlib.md5() # calculate hash sum
            self.file.seek(0)
            while True:
                data= self.file.read(8192)
                if not data: break
                m.update(data)
            self.file.seek(0)
            self.hash = m.hexdigest()

        rval = super(Document, self).save(**kwargs)

        if self.status == 'deleted':
            self.page_set.all().delete()
            
        return rval

def _post_document_save(sender, **kwargs):
    # hack for situations where there is no celerybeat
    if settings.CELERY_ALWAYS_EAGER:
        from ecs.documents.tasks import document_tamer
        document_tamer.delay().get()
    
class Page(models.Model):
    doc = models.ForeignKey(Document)
    num = models.PositiveIntegerField()
    text = models.TextField()        

    objects = AuthorizationManager()

def _post_page_delete(sender, **kwargs):
    from haystack import site
    site.get_index(Page).remove_object(kwargs['instance'])

post_delete.connect(_post_page_delete, sender=Page)
post_save.connect(_post_document_save, sender=Document)


class DownloadHistory(models.Model):
    document = models.ForeignKey(Document, db_index=True)
    user = models.ForeignKey(User)
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['downloaded_at']
