from flask import render_template, request
from flask.views import View
from sqlalchemy.orm import joinedload

from matcher.mixins import DbMixin
from matcher.scheme.platform import Platform, Scrap

from ..forms.scraps import ScrapListFilter

__all__ = ['ScrapListView']


class ScrapListView(View, DbMixin):
    def dispatch_request(self):
        form = ScrapListFilter(request.args)
        form.platforms.text_map = lambda l: self.query(Platform.slug, Platform.name).filter(Platform.slug.in_(l))
        query = self.query(Scrap).options(joinedload(Scrap.platform))

        if form.validate():
            if form.platforms.data:
                query = query.\
                    join(Platform).\
                    filter(Platform.slug.in_(form.platforms.data))

            if form.status.data:
                query = query.\
                    filter(Scrap.status.in_(form.status.data))

        ctx = {}
        ctx['search_form'] = form
        ctx['page'] = query.paginate()

        return render_template('scraps/list.html', **ctx)
