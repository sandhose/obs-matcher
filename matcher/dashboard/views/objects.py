from flask import render_template
from flask.views import View
from sqlalchemy.orm import joinedload, lazyload

from matcher.mixins import DbMixin
from matcher.scheme.enums import ExternalObjectType
from matcher.scheme.export import AttributesWrapper
from matcher.scheme.object import Episode, ExternalObject, ObjectLink
from matcher.scheme.value import Value, ValueSource

__all__ = ['ObjectListView']


class ObjectListView(View, DbMixin):
    def dispatch_request(self):
        ctx = {}
        ctx['page'] = self.query(ExternalObject).options(joinedload(ExternalObject.attributes)).paginate()

        return render_template('objects/list.html', **ctx)


class ShowObjectView(View, DbMixin):
    def dispatch_request(self, id):
        external_object = self.query(ExternalObject).options(
            joinedload(ExternalObject.attributes),
            lazyload(ExternalObject.values).joinedload(Value.sources).joinedload(ValueSource.platform),
            lazyload(ExternalObject.links).joinedload(ObjectLink.platform)
        ).get_or_404(id)

        ctx = {}
        ctx['object'] = external_object
        ctx['attributes'] = AttributesWrapper(external_object.attributes)

        if external_object.type == ExternalObjectType.SERIES:
            ctx['episodes'] = self.query(Episode).\
                filter(Episode.series_id == external_object.id).\
                options(joinedload(Episode.external_object).joinedload(ExternalObject.attributes)).\
                all()
        elif external_object.type == ExternalObjectType.EPISODE:
            res = self.query(ExternalObject, Episode).\
                join(Episode, Episode.series_id == ExternalObject.id).\
                filter(Episode.external_object_id == external_object.id).\
                options(joinedload(ExternalObject.attributes)).\
                first()

            if res:
                ctx['series'] = res[0]
                ctx['episode'] = res[1]
            else:
                ctx['series'] = None
                ctx['episode'] = None

        return render_template('objects/show.html', **ctx)
