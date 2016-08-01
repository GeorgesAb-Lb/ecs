import uuid

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User

class EthicsCommission(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=120)
    address_1 = models.CharField(max_length=120)
    address_2 = models.CharField(max_length=120)
    zip_code = models.CharField(max_length=10)
    city = models.CharField(max_length=80)
    contactname = models.CharField(max_length=120, null=True)
    chairperson = models.CharField(max_length=120, null=True)
    email = models.EmailField(null=True)
    url = models.URLField(null=True)
    phone = models.CharField(max_length=60, null=True)
    fax = models.CharField(max_length=60, null=True)
    vote_receiver = models.EmailField(null=True, blank=True)
    
    def __str__(self):
        return self.name
        
    @property
    def system(self):
        return self.uuid == uuid.UUID(settings.ETHICS_COMMISSION_UUID)

class MedicalCategory(models.Model):
    name = models.CharField(max_length=60)
    abbrev = models.CharField(max_length=12, unique=True)
    users = models.ManyToManyField(User, related_name='medical_categories')

    def __str__(self):
        return '%s (%s)' % (self.name, self.abbrev)

class AdvancedSettings(models.Model):
    default_contact = models.ForeignKey(User)
    display_notifications_in_protocol = models.BooleanField(default=False)
    display_biased_in_amendment_answer_pdf = models.BooleanField(default=True)
