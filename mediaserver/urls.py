#!/usr/bin/env python2.4
# -*- coding: utf-8 -*-

from django.conf.urls.defaults import *

urlpatterns = patterns(
    '',
    url(r'^(?P<id>\d+)/(?P<bigpage>\d+)/(?P<zoom>[^/]+)/$', 'ecs.mediaserver.views.image'),
)
