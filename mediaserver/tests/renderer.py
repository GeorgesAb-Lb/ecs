import os
import binascii
import tempfile
import math

from django.conf import settings
from uuid import uuid4

from ecs.utils.testcases import EcsTestCase
from ecs.utils.pdfutils import pdf_page_count, Page
from ecs.mediaserver.utils import MediaProvider


class RendererTest(EcsTestCase):
    '''Tests for the MediaProvider module
    
    Test for the rendering functionality that render pdf documents as png images.
    '''
    
    png_magic = binascii.a2b_hex('89504E470D0A1A0A')
    
    def setUp(self):
        super(RendererTest, self).setUp()
        self.uuid = uuid4().get_hex();
        self.pdfdoc = os.path.join(os.path.dirname(__file__), 'menschenrechtserklaerung.pdf')    
        self.f_pdfdoc = open(self.pdfdoc, "rb")
        self.pages = pdf_page_count(self.f_pdfdoc)
        self.render_dirname = tempfile.mkdtemp()
    
    def tearDown(self):
        super(RendererTest, self).tearDown()
        # shutil.rmtree(self.render_dirname)
        
    def testPngRendering(self):
        '''Tests that PNG renderer produces png images and that the right amount of pages is produced,
        when rendering a pdf document.
        '''
        
        tiles = settings.MS_SHARED["tiles"]
        resolutions = settings.MS_SHARED["resolutions"]
        
        pages_expected = []
        for tx, ty in tiles:
            for w in resolutions:
                n = tx * ty
                tilepages = int(math.ceil(self.pages / float(n)))
                print tilepages
                for p in range(1, tilepages + 1):
                    pages_expected += [Page(self.uuid, tx, ty, w, p)]

        pages_real = []
        
        mp = MediaProvider()
        
        for page, data in mp._render_pages(self.uuid, self.f_pdfdoc, self.render_dirname):
            # check for png magic
            current_magic = data.read(len(self.png_magic))
            self.assertTrue(current_magic == self.png_magic)
            if hasattr(data, "close"):
                data.close()
            pages_real.append(page)
        
        self.assertEqual(len(pages_expected), len(pages_real))
    
