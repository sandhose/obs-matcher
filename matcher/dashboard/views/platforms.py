from flask import render_template
from flask.views import View

from matcher.mixins import DbMixin
from matcher.scheme.platform import Platform

__all__ = ['PlatformListView']


class PlatformListView(View, DbMixin):
    def dispatch_request(self):
        ctx = {}

        ctx['page'] = self.query(Platform).paginate()

        return render_template('platforms/list.html', **ctx)
