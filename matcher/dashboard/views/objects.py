import re

from flask import render_template, request
from flask.views import View
from sqlalchemy import func
from sqlalchemy.orm import contains_eager, joinedload, lazyload, undefer

from matcher.mixins import DbMixin
from matcher.scheme.enums import ExternalObjectType
from matcher.scheme.export import AttributesWrapper
from matcher.scheme.object import Episode, ExternalObject, ObjectLink
from matcher.scheme.platform import Platform, Scrap, Session
from matcher.scheme.value import Value, ValueSource
from matcher.scheme.views import AttributesView

from ..forms.objects import ObjectListFilter

__all__ = ['ObjectListView', 'ShowObjectView']


class ObjectListView(View, DbMixin):
    def dispatch_request(self):
        form = ObjectListFilter(request.args)
        form.platform.query = self.query(Platform)
        form.session.query = self.query(Session)
        form.object_link.platform.query = self.query(Platform)

        query = self.query(ExternalObject).\
            options(undefer(ExternalObject.links_count)).\
            order_by(ExternalObject.id)

        # Join the needed columns for filtering
        if form.platform.data \
                or (form.object_link.platform.data and form.object_link.external_id.data) \
                or form.session.data \
                or form.scrap.data:
            query = query.join(ExternalObject.links)

        if form.session.data or form.scrap.data:
            query = query.join(ObjectLink.scraps)

        if form.search.data or form.country.data:
            query = query.join(ExternalObject.attributes).\
                options(contains_eager(ExternalObject.attributes))
        else:
            # If we are not filtering using the attributes we need to join-load them
            query = query.options(joinedload(ExternalObject.attributes))

        # Apply the filters
        if form.search.data:
            q = func.to_tsquery(re.sub(' +', ' & ', form.search.data))
            query = query.filter(AttributesView.search_vector.op('@@')(q)).\
                order_by(func.ts_rank(AttributesView.search_vector, q))
        else:
            query = query.order_by(ExternalObject.id)

        if form.country.data:
            query = query.filter(AttributesView.countries[1].
                                 in_(c.strip() for c in form.country.data.upper().split(',')))

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
                                 ObjectLink.external_id.contains(form.object_link.external_id.data))

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
