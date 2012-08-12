import urlparse
from django.template import Library
from django.template.defaulttags import URLNode, url
from django.contrib.sites.models import Site
from django.core.urlresolvers import NoReverseMatch

register = Library()

class SiteURLNode(URLNode):
    def render(self, context):
        try:
            return super(SiteURLNode, self).render(context)
        except NoReverseMatch:
            self.kwargs.pop('site_id')
        return super(SiteURLNode, self).render(context)

def site_url(parser, token, node_cls=SiteURLNode):
    """Just like {% url %} but ads the domain of the current site."""
    node_instance = url(parser, token)
    return node_cls(view_name=node_instance.view_name,
        args=node_instance.args,
        kwargs=node_instance.kwargs,
        asvar=node_instance.asvar)
site_url = register.tag(site_url)
