from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.template.loader import get_template

from ecs.core.serializer import Serializer
from ecs.utils.pdfutils import html2pdf


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('-o', action='store', dest='outfile', help='output file', default=None),
        make_option('-t', dest='output_type', action='store', default='html', 
        help="""--type can be one of 'html' or 'pdf'
-o outputfile"""),
    )

    def handle(self, **options):
        if options['output_type'] not in ['html', 'pdf']:
            raise CommandError('Error: --type must be one of "html", "pdf"')
        if not options['outfile']: 
            raise CommandError('Error: Outputfile "-o filename" must be specified')
        
        ecxf = Serializer()
        tpl = get_template('docs/ecx/base.html')
        html = tpl.render({
            'version': ecxf.version,
            'fields': ecxf.docs(),
        }).encode('utf-8')
            
        with open(options['outfile'], 'wb') as f:                    
            if options['output_type'] == "html":
                f.write(html)
            else:
                f.write(html2pdf(html))

    
