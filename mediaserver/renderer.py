import subprocess
import tempfile
from django.conf import settings
from ecs.mediaserver.cacheobjects import MediaBlob, Docshot
import os
from uuid import UUID

MONTAGE_PATH = getattr(settings, 'IMAGEMAGICK_MONTAGE_PATH', '/usr/bin/montage')
DEFAULT_ASPECT_RATIO = 1.41428
DEFAULT_DPI = 72
DEFAULT_DEPTH = 8
    
def renderPDFMontage(uuid, tmp_rendersrc, width, tiles_x, tiles_y, aspect_ratio=DEFAULT_ASPECT_RATIO, dpi=DEFAULT_DPI, depth=DEFAULT_DEPTH):    
    margin_x = 0
    margin_y = 0
    
    if tiles_x > 1 and tiles_y > 1:
        margin_x = 4
        margin_y = 4

    height=width/aspect_ratio
    tile_width = (width / tiles_x) - margin_x
    tile_height = (height / tiles_y) - margin_y
    
    tmp_renderdir = tempfile.mkdtemp() 
    tmp_docshot_prefix = os.path.join(tmp_renderdir, '%s_%s_%sx%s_' % (uuid, width, tiles_x, tiles_y)) + "%d"
     
    args = '%s -verbose -geometry %dx%d+%d+%d -tile %dx%d -density %d -depth %d %s PNG:%s' % (MONTAGE_PATH, tile_height, tile_width,margin_x, margin_y,tiles_x, tiles_y, dpi, depth, tmp_rendersrc, tmp_docshot_prefix)
    popen = subprocess.Popen(args, stderr=subprocess.PIPE ,shell=True)
    returncode = popen.wait()
    
    if returncode != 0:
        raise IOError('montage returned error code:%d %s' % (returncode, popen.stderr.read()))

    pagenr = 0
    
    for ds in sorted(os.listdir(tmp_renderdir)):
        dspath = os.path.join(tmp_renderdir, ds)
        pagenr += 1
        yield Docshot(MediaBlob(UUID(uuid)), tiles_x, tiles_y, width, pagenr), open(dspath,"rb")

def renderDefaultDocshots(pdfblob, filelike):
    tiles = [ 1, 3, 5 ]
    width = [ 800, 768 ] 
    
    # prepare the temporary render src
    tmp_rendersrc = tempfile.mktemp();
    with open(tmp_rendersrc, "wb") as f_rendersrc:
        f_rendersrc.write(filelike.read());

    for t in tiles:
        for w in width:
            for docshot, data in renderPDFMontage(pdfblob.cacheID(), tmp_rendersrc, w, t, t):
                yield docshot, data
