# -*- coding: utf-8 -*-

from uuid import uuid4
from time import time

from ecs.utils.testcases import EcsTestCase
from ecs.mediaserver.utils import AuthUrl

class AuthUrlTest(EcsTestCase):
    '''Tests for the AuthUrl module
    
    Tests for 'AuthUrls' which have implicit encoded permissions and timestamps for
    allowing and denying access to data provided by the mediaserver.
    '''
    
    baseurl =  "http://void"
    bucket = "/"
    keyid = "CyKK3sUdWCVxOMIvoyW8"
    keysecret = "7GEVGvImpCIxidINqA3MEOU5zBJDeCf"
    
    def testConsistency(self):
        '''Tests the expiration of URLs for media on the mediaserver.
        '''
        
        uuid = uuid4()
        hasExpired = int(time())
        willExpire = hasExpired + 60
        
        authurl = AuthUrl(self.keyid, self.keysecret)
        url = authurl.grant(self.baseurl, self.bucket, uuid.get_hex(), self.keyid, willExpire)
        bucket, objectid, keyid, expires, signature = authurl.parse(url)
        self.assertEqual(authurl.verify_parsed(bucket, objectid, keyid, expires, signature), True)
        self.assertEqual(authurl.verify(url), True)
        
        url = authurl.grant(self.baseurl, self.bucket, uuid.get_hex(), self.keyid, hasExpired)
        bucket, objectid, keyid, expires, signature = authurl.parse(url)
        self.assertEqual(authurl.verify_parsed(bucket, objectid, keyid, expires, signature), False)
        self.assertEqual(authurl.verify(url), False)
        