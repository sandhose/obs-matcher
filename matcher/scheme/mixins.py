class ResourceMixin(object):
    """A mixin to automatically add the API endpoints, with self linking"""

    # TODO: remove or replace this

    @classmethod
    def register_api(cls, app, prefix, resource):
        # FIXME
        pass

    @property
    def self_link(self):
        # FIXME
        return ''
