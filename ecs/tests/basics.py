# -*- coding: utf-8 -*-
#
# (c) 2010 Medizinische Universität Wien
#
"""
Unittests for the site
"""
from ecs.utils.testcases import EcsTestCase

class BasicImportTests(EcsTestCase):
    """Tests for most basic importability of core modules
    """
    
    def test_import(self,):
        """Tests if settings and urls modules are importable. Simple but quite useful.
        """
    
        from ecs import settings
        from ecs import urls
