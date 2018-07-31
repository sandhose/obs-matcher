import datetime

from flask import render_template
from flask.views import View
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from matcher.mixins import DbMixin
from matcher.scheme.enums import ScrapStatus
from matcher.scheme.object import ExternalObject, ObjectLink
from matcher.scheme.platform import Platform, Scrap

__all__ = ['HomeView']


class HomeView(View, DbMixin):
    def dispatch_request(self):
        ctx = {}
        ctx['external_object_stats'] = {key.name: value for (key, value) in
                                        self.query(ExternalObject.type,
                                                   func.count(ExternalObject.id))
                                        .group_by(ExternalObject.type)}
        ctx['platforms_stats'] = {key.name: value for (key, value) in
                                  self.query(Platform.type,
                                             func.count(Platform.id)).group_by(Platform.type)}
        ctx['object_link_count'] = self.query(ObjectLink).count()

        now = datetime.datetime.utcnow()

        def successful_scrap(timedelta):
            return (
                self
                .query(Scrap)
                .filter(Scrap.date >= (now - timedelta))
                .filter(Scrap.status == ScrapStatus.SUCCESS)
                .count()
            )

        ctx['recent_scraps_count'] = {
            'day': successful_scrap(datetime.timedelta(days=1)),
            'week': successful_scrap(datetime.timedelta(weeks=1)),
            'month': successful_scrap(datetime.timedelta(days=30)),
            'year': successful_scrap(datetime.timedelta(days=365)),
        }

        ctx['last_scraps'] = self.query(Scrap).options(joinedload(Scrap.platform))[-9:]
        return render_template('home.html', **ctx)
