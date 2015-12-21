# -*- coding: utf-8 -*-
from celery.task import task
from haystack import site

from ecs.help.models import Page


@task()
def index_help_page(page_pk=None):
    logger = index_help_page.get_logger()
    try:
        page = Page.objects.get(pk=page_pk)
    except Page.DoesNotExist:
        logger.warning("Warning, help page with pk %s does not exist" % str(page_pk))
        return False

    index = site.get_index(Page)
    index.update_object(page)

    return True
