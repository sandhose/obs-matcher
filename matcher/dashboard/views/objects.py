from flask import render_template, request
from flask.views import View
from sqlalchemy.orm import joinedload, lazyload, undefer

from matcher.mixins import DbMixin
from matcher.scheme.enums import ExternalObjectType
from matcher.scheme.export import AttributesWrapper
from matcher.scheme.object import Episode, ExternalObject, ObjectLink
from matcher.scheme.platform import Platform, Scrap, Session
from matcher.scheme.value import Value, ValueSource

from ..forms.objects import ObjectListFilter

__all__ = ['ObjectListView', 'ShowObjectView']


class ObjectListView(View, DbMixin):
    def dispatch_request(self):
        form = ObjectListFilter(request.args)
        form.platform.query = self.query(Platform)
        form.session.query = self.query(Session)
        form.object_link.platform.query = self.query(Platform)

        query = self.query(ExternalObject).\
            options(joinedload(ExternalObject.attributes),
                    undefer(ExternalObject.links_count)).\
            order_by(ExternalObject.id)

        if form.platform.data \
                or (form.object_link.platform.data and form.object_link.external_id.data) \
                or form.session.data \
                or form.scrap.data:
            query = query.join(ExternalObject.links)

        if form.session.data or form.scrap.data:
            query = query.join(ObjectLink.scraps)

        if form.search.data:
            pass  # TODO

        if form.type.data:
            query = query.filter(ExternalObject.type.in_(form.type.data))
        else:
            # FIXME: ignore PERSONs by default for now
            query = query.filter(ExternalObject.type != ExternalObjectType.PERSON)

        if form.platform.data:
            query = query.filter(ObjectLink.platform_id.in_(platform.id for platform in form.platform.data))

        if form.scrap.data:
            query = query.filter(Scrap.id == form.scrap.data)

        if form.session.data:
            query = query.join(Scrap.sessions).\
                filter(Session.id.in_(s.id for s in form.session.data))

        if form.object_link.platform.data and form.object_link.external_id.data:
            query = query.filter(ObjectLink.platform == form.object_link.platform.data,
                                 ObjectLink.external_id == form.object_link.external_id.data)

        ctx = {}
        ctx['page'] = query.paginate()
        ctx['filter_form'] = form

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
