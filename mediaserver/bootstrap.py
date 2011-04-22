# -*- coding: utf-8 -*-
import os.path

from django.conf import settings

from ecs import bootstrap
from ecs.utils import gpgutils
from ecs.mediaserver.utils import MediaProvider

@bootstrap.register()
def import_decryption_key():
    gpgutils.reset_keystore(settings.STORAGE_DECRYPT ["gpghome"])
    gpgutils.import_key(settings.STORAGE_DECRYPT ["key"], settings.STORAGE_DECRYPT ["gpghome"])

@bootstrap.register()
def create_local_storage_vault():
    workdir = settings.STORAGE_VAULT_OPTIONS['LocalFileStorageVault.rootdir']
    if workdir:
        if not os.path.isdir(workdir):
            os.makedirs(workdir)

@bootstrap.register()
def create_disk_caches():
    m = MediaProvider(allow_mkrootdir=True)

    