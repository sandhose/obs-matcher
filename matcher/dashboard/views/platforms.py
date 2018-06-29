from flask import render_template, request
from flask.views import View

from matcher.mixins import DbMixin
from matcher.scheme.platform import Platform

from ..forms.platforms import PlatformListFilter

__all__ = ['PlatformListView']


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
