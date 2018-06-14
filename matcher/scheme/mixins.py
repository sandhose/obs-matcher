from flask import url_for

from ..api_old.index import IndexView


class ResourceMixin(object):
    """A mixin to automatically add the API endpoints, with self linking"""

    @classmethod
    def register_api(cls, app, prefix, resource):
        cls.api_prefix = prefix
        app.add_url_rule('/{}/<pk>/'.format(prefix),
                         endpoint='{}_detail'.format(prefix),
                         view_func=resource.as_detail(),
                         methods=['GET', 'POST', 'PUT', 'DELETE'])

        app.add_url_rule('/{}/'.format(prefix),
                         endpoint='{}_list'.format(prefix),
                         view_func=resource.as_list(),
                         methods=['GET', 'POST', 'PUT', 'DELETE'])
        IndexView.register_api(prefix, 'api.{}_list'.format(prefix))

    @property
    def self_link(self):
        return url_for('api.{}_detail'.format(self.__class__.api_prefix),
                       pk=self.id, _external=True)
