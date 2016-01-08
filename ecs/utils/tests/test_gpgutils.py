import os, tempfile
from django.conf import settings
from ecs.utils.testcases import EcsTestCase
from ecs.utils.gpgutils import encrypt_sign, decrypt_verify, reset_keystore, gen_keypair, import_key

class Gpgutilstest(EcsTestCase):
    '''Tests for the gpgutils module
    
    Tests for data encryption, decryption and signature verification.
    '''
    
    def setUp(self):
        super(Gpgutilstest, self).setUp()
        
        self.encrypt_gpghome = settings.STORAGE_ENCRYPT ['gpghome']
        self.encrypt_owner = settings.STORAGE_ENCRYPT['encrypt_owner']
        self.signing_owner = settings.STORAGE_ENCRYPT['signing_owner']
        
        self.decrypt_gpghome = settings.STORAGE_DECRYPT ['gpghome']
        self.decrypt_owner = settings.STORAGE_DECRYPT['decrypt_owner']
        self.verify_owner = settings.STORAGE_DECRYPT['verify_owner'] 


    def fresh_temporary_entities(self):
        self.testdir = tempfile.mkdtemp()
        self.authority_name = "ecs_authority"
        self.mediaserver_name = "ecs_mediaserver"
        
        # create encrypt gpghome and set encrypt signing owner
        self.encrypt_gpghome = os.path.join(self.testdir, self.authority_name)
        self.encrypt_owner = self.mediaserver_name
        self.signing_owner = self.authority_name
        os.mkdir(self.encrypt_gpghome)
        
        # create decrypt gpghome and set decrypt verify owner
        self.decrypt_gpghome= os.path.join(self.testdir, self.mediaserver_name)
        self.decrypt_owner = self.mediaserver_name
        self.verify_owner = self.authority_name
        os.mkdir(self.decrypt_gpghome)
        
        # generate keypair files for authority
        auth_sec_name = os.path.join(self.testdir, self.authority_name+".sec")
        auth_pub_name = os.path.join(self.testdir, self.authority_name+".pub")
        gen_keypair(self.authority_name, auth_sec_name, auth_pub_name)
        
        # generate keypair files for mediaserver
        ms_sec_name = os.path.join(self.testdir, self.mediaserver_name+".sec")
        ms_pub_name = os.path.join(self.testdir, self.mediaserver_name+".pub")
        gen_keypair(self.mediaserver_name, ms_sec_name, ms_pub_name)

        # import secretkey of authority and public key of mediaserver to authority        
        import_key(auth_sec_name, self.encrypt_gpghome)
        import_key(ms_pub_name, self.encrypt_gpghome)
        
        # import secretkey of mediaserver and public key of authority to mediaserver
        import_key(ms_sec_name, self.decrypt_gpghome)
        import_key(auth_pub_name, self.decrypt_gpghome)


    def testConsistency(self):
        '''Tests if data can be encrypted and signed and then if it can be decrypted and verified via gpg and that it matches the previously encrypted test data.'''
        
        # self.fresh_temporary_entities()
        self.testdata=b"im very happy to be testdata"

        osdescriptor, encryptedfilename = tempfile.mkstemp()
        os.close(osdescriptor)

        try:
            with tempfile.TemporaryFile() as inputfile:
                inputfile.write(self.testdata)
                inputfile.seek(0)
                encrypt_sign(inputfile, encryptedfilename, self.encrypt_gpghome,
                    self.encrypt_owner, self.signing_owner)

            decryptedfile = decrypt_verify(encryptedfilename,
                self.decrypt_gpghome, self.decrypt_owner, self.verify_owner)

            self.assertNotEqual(self.testdata, open(encryptedfilename, 'rb').read())
            self.assertEqual(self.testdata, decryptedfile.read())
        finally:
            if os.path.exists(encryptedfilename):
                os.remove(encryptedfilename)
