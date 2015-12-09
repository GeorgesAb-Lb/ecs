import subprocess
import os
import tempfile
import shutil
import re


class CA(object):
    def __init__(self, basedir, **kwargs):
        self.basedir = basedir
        self.certs = 'certs'
        self.crl_dir = 'crl'
        self.database = 'index.txt'
        self.new_certs_dir = 'newcerts'
        self.certificate = 'ca.cert.pem'
        self.serial = 'serial'
        self.crlnumber = 'crlnumber'
        self.crl = 'crl.pem'
        self.private_key = 'private/ca.key.pem'
        self.default_days = 2 * 365
        self.default_bits = 2048
        self.config = 'openssl.cnf'

        for key, value in kwargs.items():
            setattr(self, key, value)
        
    def _exec(self, cmd):
        return subprocess.check_output(['openssl'] + cmd)
        
    def _exec_ca(self, cmd):
        return self._exec(['ca', '-config', self.config, '-batch'] + cmd)

    @property
    def ca_key_path(self):
        return os.path.join(self.basedir, self.private_key)
        
    @property
    def crl_path(self):
        return os.path.join(self.basedir, self.crl)
        
    @property
    def ca_cert_path(self):
        return os.path.join(self.basedir, self.certificate)
        
    def _gen_crl(self):
        self._exec_ca(['-gencrl', '-crldays', '3650', '-out', self.crl_path])

    def setup(self, subject, key_length=2048):
        if not os.path.exists(os.path.join(self.basedir, 'private')):
            for dirname in [self.certs, self.crl_dir, self.new_certs_dir]:
                os.makedirs(os.path.join(self.basedir, dirname), 0755)
            os.makedirs(os.path.join(self.basedir, 'private'), 0700)
            open(os.path.join(self.basedir, self.database), 'a').close()
            with open(os.path.join(self.basedir, self.crlnumber), 'w') as f:
                f.write('01')
            with open(os.path.join(self.basedir, self.serial), 'w') as f:
                f.write('01')
                
        if not os.path.exists(self.ca_key_path):
            self._exec(['genrsa', '-out', self.ca_key_path, str(key_length)])
        if not os.path.exists(self.ca_cert_path):
            self._exec(['req', '-batch', '-new', '-key', self.ca_key_path, '-x509', '-days', '3650', '-subj', subject, '-out', self.ca_cert_path])
        if not os.path.exists(self.crl_path):
            self._gen_crl()
    
    def get_fingerprint(self, cert):
        return self._exec(['x509', '-noout', '-fingerprint', '-in', cert]).split('=')[1].strip()
        
    def get_serial(self, cert):
        return self._exec(['x509', '-noout', '-serial', '-in', cert]).split('=')[1].strip()
        
    def get_hash(self, cert):
        return self._exec(['x509', '-noout', '-hash', '-in', cert]).strip()

    @property
    def ca_fingerprint(self):
        return self.get_fingerprint(self.ca_cert_path)
        
    def get_cert_path_for_fingerprint(self, fingerprint):
        return os.path.join(self.basedir, self.certs, '%s.pem' % fingerprint.replace(':', ''))
        
    def make_cert(self, subject, pkcs12_file, key_length=None, days=None, passphrase=''):
        workdir = tempfile.mkdtemp()
        try:
            key_file = os.path.join(workdir, 'key.pem')
            csr_file = os.path.join(workdir, 'x.csr')
            cert_file = os.path.join(workdir, 'cert.pem')
            
            # generate a key and a certificate signing request
            self._exec(['genrsa', '-out', key_file])
            self._exec(['req', '-batch', '-new', '-key', key_file, '-out', csr_file, '-subj', subject])
            
            # sign the request
            to_be_signed = ['-in', csr_file, '-out', cert_file] 
            if days:
                to_be_signed += ['-days', str(days)]
            self._exec_ca(to_be_signed)
            
            fingerprint = self.get_fingerprint(cert_file)
            shutil.copyfile(cert_file, self.get_cert_path_for_fingerprint(fingerprint))
            
            # create a browser compatible certificate
            self._exec(['pkcs12', '-export', '-clcerts', '-in', cert_file, '-inkey', key_file, '-out', pkcs12_file, '-passout', 'pass:%s' % passphrase])
            return fingerprint

        finally:
            shutil.rmtree(workdir)

    def is_revoked(self, cert):
        output = self._exec(['crl', '-text', '-noout', '-in', self.crl_path])

        serial_re = re.compile('^\s+Serial\sNumber\:\s+(\w+)')
        lines = output.split('\n')
        serial = self.get_serial(cert)

        for line in lines:
            match = serial_re.match(line)
            if match and match.group(1) == serial:
                return True
        return False

    def revoke(self, cert):
        if self.is_revoked(cert):
            return False
        self._exec_ca(['-revoke', cert])
        self._gen_crl()
        return True

    def revoke_by_fingerprint(self, fingerprint):
        return self.revoke(self.get_cert_path_for_fingerprint(fingerprint))

