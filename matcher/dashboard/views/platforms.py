import datetime

from flask import abort, render_template, request
from flask.views import View
from sqlalchemy import func

from matcher.mixins import DbMixin
from matcher.scheme.object import ExternalObject, ObjectLink
from matcher.scheme.platform import Platform, Scrap

from ..forms.platforms import PlatformListFilter

__all__ = ['PlatformListView', 'ShowPlatformView']


class PlatformListView(View, DbMixin):
    def dispatch_request(self):
        form = PlatformListFilter(request.args)
        form.country.query = self.query(Platform.country).group_by(Platform.country).order_by(Platform.country)
        query = self.query(Platform)

        if form.validate():
            if form.search.data:
                query = query.filter(Platform.search_filter(form.search.data))

            if form.type.data:
                query = query.filter(Platform.type.in_(form.type.data))

            if form.country.data:
                query = query.filter(Platform.country.in_(form.country.data))

        ctx = {}
        ctx['filter_form'] = form
        ctx['page'] = query.paginate()

        return render_template('platforms/list.html', **ctx)


class ShowPlatformView(View, DbMixin):
    def dispatch_request(self, slug):
        platform = self.query(Platform).filter(Platform.slug == slug).first()

        if platform is None:
            abort(404)

        ctx = {}
        ctx['platform'] = platform
        ctx['link_stats'] = {type_.name: count for (type_, count) in (
            self.query(ExternalObject.type, func.count(ExternalObject.id)).
            join(ObjectLink).
            filter(ObjectLink.platform == platform).
            group_by(ExternalObject.type)
        )}

        now = datetime.datetime.utcnow()

        def last_scraps(timedelta):
            return (
                self
                .query(Scrap)
                .filter(Scrap.date >= (now - timedelta))
                .filter(Scrap.platform == platform)
                .count()
            )

        ctx['recent_scraps_count'] = {
            'week': last_scraps(datetime.timedelta(weeks=1)),
            'month': last_scraps(datetime.timedelta(days=30)),
            'year': last_scraps(datetime.timedelta(days=365)),
        }

        ctx['objects_sample'] = (
            self.query(ExternalObject).
            filter(ExternalObject.id.in_(self.query(ObjectLink.external_object_id).
                                         filter(ObjectLink.platform == platform))).
            order_by(func.random())
        )

        return render_template('platforms/show.html', **ctx)
