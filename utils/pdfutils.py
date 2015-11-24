# -*- coding: utf-8 -*-
'''
========
pdfutils
========

- identification (is valid pdf, number of pages), 
- manipulation (barcode stamp)
- conversion (to PDF/A, to text)
- creation (from html)

'''
import os, subprocess, tempfile, logging, copy, shutil
from cStringIO import StringIO

from django.conf import settings
from django.template import Context, loader
from django.utils.encoding import smart_str

from ecs.utils.pathutils import which_path

GHOSTSCRIPT_PATH = which_path('ECS_GHOSTSCRIPT', 'gs')
WKHTMLTOPDF_PATH = which_path('ECS_WKHTMLTOPDF', 'wkhtmltopdf', extlist=["-amd64", "-i386"])
QPDF_PATH = which_path('ECS_QPDF', 'qpdf')
PDFTK_PATH = which_path('ECS_PDFTK', 'pdftk')

PDF_MAGIC = r"%PDF-"

pdfutils_logger = logging.getLogger(__name__)

class Page(object):
    ''' Properties of a image of an page of an pageable media (id, tiles_x, tiles_y, width, pagenr)
    '''
    def __init__(self, id, tiles_x, tiles_y, width, pagenr):
        self.id = id
        self.tiles_x = tiles_x
        self.tiles_y = tiles_y
        self.width = width
        self.pagenr = pagenr

    def __repr__(self):
        return str("%s_%s_%sx%s_%s" % (self.id, self.width, self.tiles_x, self.tiles_y , self.pagenr))

        
def _pdf_stamp(source_filelike, dest_filelike, stamp_filename):
    ''' takes source pdf, stamps another stamp_filename pdf onto every page of source and output it to dest
    
    :raise IOError: if something goes wrong (including exit errorcode and stderr output attached)
    '''  
    source_filelike.seek(0)
    cmd = [PDFTK_PATH, '-', 'stamp', stamp_filename, 'output', '-', 'dont_ask']
    popen = subprocess.Popen(cmd, bufsize=-1, stdin=source_filelike, stdout=dest_filelike, stderr=subprocess.PIPE)       
    stdout, stderr = popen.communicate()
    source_filelike.seek(0)
    if popen.returncode != 0:
        raise IOError('stamp pipeline returned with errorcode %i , stderr: %s' % (popen.returncode, stderr))


def pdf_barcodestamp(source_filelike, dest_filelike, barcode1, barcode2=None, barcodetype="qrcode", timeoutseconds=30):
    ''' takes source pdf, stamps a barcode onto every page and output it to dest
    
    :raise IOError: if something goes wrong (including exit errorcode and stderr output attached)
    ''' 
    S_BARCODE_TEMPLATE = """
        gsave 
        {{ moveto }} moveto {{ scale }} scale {{ rotate }} rotate
        ({{ header }}{{ barcode }}) ({{options}}) /{{barcodetype}} /uk.co.terryburton.bwipp findresource exec
        grestore
        """
    D_CODE128 = {'moveto': '50 600', 'scale': '0.5 0.5', 'rotate': '89.999', 
        'header': '^104', 'options': 'includetext', 'barcodetype': "code128",
        }
    D_QRCODE =  {'moveto': '20 100', 'scale': '0.5 0.5', 'rotate': '0', 
        'header': '', 'options': '', 'barcodetype': "qrcode",
        }
    barcode1dict = copy.deepcopy(D_QRCODE)
    barcode1dict['barcode']= barcode1
    barcode1s = loader.get_template_from_string(S_BARCODE_TEMPLATE).render(Context(barcode1dict))
      
    if barcode2:
        barcode2dict = copy.deepcopy(D_QRCODE)
        barcode2dict['moveto'] = '20 600'
        barcode2dict['barcode'] =  barcode2
        barcode2s = loader.get_template_from_string(S_BARCODE_TEMPLATE).render(Context(barcode2dict))
    else:
        barcode2s = ""
    
    # render barcode template to ready to use postscript file
    template = loader.get_template_from_string("""{{barcode1}}{{barcode2}}""")
    barcode_ps = loader.render_to_string('wkhtml2pdf/barcode.ps')+ template.render(Context({
        'barcode1': barcode1s, 'barcode2': barcode2s,}))
    
    try:
        # render barcode postscript file to pdf
        barcode_pdf_oshandle, barcode_pdf_name = tempfile.mkstemp(suffix='.pdf') 
        cmd = [GHOSTSCRIPT_PATH, 
            '-q', '-dNOPAUSE', '-dBATCH', '-sDEVICE=pdfwrite', '-sPAPERSIZE=a4', '-dAutoRotatePages=/None', 
            '-sOutputFile=%s' % barcode_pdf_name, '-c', '<</Orientation 0>> setpagedevice', '-']
        popen = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = popen.communicate(barcode_ps)
        if popen.returncode != 0:
            raise IOError('barcode processing using ghostscript returned error code %i , stderr: %s' % (popen.returncode, stderr))        
    finally:    
        os.close(barcode_pdf_oshandle)
    
    # implant barcode pdf to source pdf on every page 
    _pdf_stamp(source_filelike, dest_filelike, barcode_pdf_name)
    
    if os.path.isfile(barcode_pdf_name):
        os.remove(barcode_pdf_name)
    
  
class PdfBroken(Exception):
    pass

def decrypt_pdf(src, logger=pdfutils_logger):
    with tempfile.NamedTemporaryFile(suffix='.pdf') as tmp:
        shutil.copyfileobj(src, tmp)
        tmp.seek(0)
        decrypted = tempfile.NamedTemporaryFile(suffix='.pdf')
        popen = subprocess.Popen([QPDF_PATH, '--decrypt', tmp.name, decrypted.name], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        stdout, stderr = popen.communicate()
        if popen.returncode in (0, 3):  # 0 == ok, 3 == warning
            if popen.returncode == 3:
                logger.warn(u'qpdf warning:\n%s', smart_str(stderr, errors='backslashreplace'))
            decrypted.seek(0)
            return decrypted
        else:
            from ecs.users.utils import get_current_user
            user = get_current_user()
            logger.warn(u'qpdf error (returncode=%s):\nUser: %s (%s)\n%s', popen.returncode, user, user.email if user else 'anonymous', smart_str(stderr, errors='backslashreplace'))
            raise PdfBroken('pdf broken')
    src.seek(0)
    return src


def wkhtml2pdf(html, header_html=None, footer_html=None, param_list=None):
    ''' Takes html and makes an pdf document out of it using the webkit engine
    '''
    if isinstance(html, unicode): 
        html = html.encode('utf-8') 
    if isinstance(header_html, unicode):
        header_html = header_html.encode('utf-8')
    if isinstance(footer_html, unicode):
        footer_html = footer_html.encode('utf-8')
    
    cmd = [WKHTMLTOPDF_PATH,
        '--margin-left', '2cm',
        '--margin-top', '2cm',
        '--margin-right', '2cm',
        '--margin-bottom', '2cm',
        '--page-size', 'A4',
    ] + getattr(settings, 'WKHTMLTOPDF_OPTIONS', [])
    tmp_dir = tempfile.mkdtemp(dir=settings.TEMPFILE_DIR)
    shutil.copytree(os.path.join(settings.PROJECT_DIR, 'utils', 'pdf'), os.path.join(tmp_dir, 'media'))

    if header_html:
        header_html_file = tempfile.NamedTemporaryFile(suffix='.html', dir=tmp_dir, delete=False)
        header_html_file.write(header_html)
        header_html_file.close()
        cmd += ['--header-html', header_html_file.name]
    if footer_html and not getattr(settings, 'DISABLE_WKHTML2PDF_FOOTERS', False):
        footer_html_file = tempfile.NamedTemporaryFile(suffix='.html', dir=tmp_dir, delete=False)
        footer_html_file.write(footer_html)
        footer_html_file.close()
        cmd += ['--footer-html', footer_html_file.name]

    if param_list:
        cmd += param_list

    html_file = tempfile.NamedTemporaryFile(suffix='.html', dir=tmp_dir, delete=False)
    html_file.write(html)
    html_file.close()
    cmd += ['page', html_file.name]

    pdf_file = tempfile.NamedTemporaryFile(suffix='.pdf', dir=tmp_dir, delete=False)
    pdf_file.close()
    cmd += [pdf_file.name]
    
    try:
        popen = subprocess.Popen(cmd, stdin=None, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = popen.communicate() 
        if popen.returncode != 0: 
            raise IOError('wkhtmltopdf pipeline returned with errorcode %i , stderr: %s' % (popen.returncode, stderr))

        with open(pdf_file.name, 'rb') as pdf:
            ret = pdf.read()

    finally:
        shutil.rmtree(tmp_dir)

    return ret
