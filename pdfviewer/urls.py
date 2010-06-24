# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *


urlpatterns = patterns(
    '',
    url(r'^demo$', 'ecs.pdfviewer.views.demo'),
    url(r'^(?P<id>[0-9a-f]+)/(?P<page>\d+)/(?P<zoom>[^/]+)/$', 'ecs.pdfviewer.views.show', name='pdf_show'),
    url(r'^(?P<did>[0-9a-f]+)/(?P<page>\d+)/(?P<zoom>[^/]+)/annotation/$', 'ecs.pdfviewer.views.annotation', name='pdf_anno'),
    url(r'^(?P<did>[0-9a-f]+)/(?P<page>\d+)/(?P<zoom>[^/]+)/annotation/delete/$', 'ecs.pdfviewer.views.delete_annotation', name='pdf_anno'),
)
