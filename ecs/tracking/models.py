from django.db import models
from django.contrib.auth.models import User
from django.core.urlresolvers import resolve, Resolver404


class ViewManager(models.Manager):
    def get_or_create_for_url(self, url):
        try:
            func, args, kwargs = resolve(url)
        except Resolver404:
            return None, False
        vary_on = []
        if hasattr(func, 'tracking_hints'):
             for name in func.tracking_hints.get('vary_on'):
                 vary_on.append('%s=%s' % (name, kwargs.get(name)))
        try:
            path = "%s.%s%s" % (func.__module__, func.__name__, "?%s" % "&".join(vary_on) if vary_on else "")
        except AttributeError:
            path = "<unknown>"
        return self.get_or_create(path=path)


class View(models.Model):
    path = models.CharField(max_length=200, db_index=True, unique=True)
    objects = ViewManager()
    
    def __str__(self):
        try:
            module, func = self.path.rsplit('.', 1)
            return "%s @ %s" % (func, module)
        except (ValueError, TypeError):
            return self.path


class Request(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    ip = models.GenericIPAddressField(protocol='ipv4', db_index=True)
    user = models.ForeignKey(User, related_name='requests')
    url = models.TextField()
    view = models.ForeignKey(View)
    anchor = models.CharField(max_length=100, db_index=True, blank=True)
    title = models.TextField(blank=True)
    content_type = models.CharField(max_length=100)
    method = models.CharField(max_length=4, choices=[('GET', 'GET'), ('POST', 'POST')], db_index=True)
    
    def save(self, **kwargs):
        if not self.view_id:
            self.view, created = View.objects.get_or_create_for_url(self.url)
        super(Request, self).save(**kwargs)
    
    def __str__(self):
        return "%s %s <-> %s" % (self.method, self.url, self.view.path)
