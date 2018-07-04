from flask import render_template
from flask.views import View
from sqlalchemy.orm import joinedload

from matcher.mixins import DbMixin
from matcher.scheme.object import ExternalObject

__all__ = ['ObjectListView']


class ObjectListView(View, DbMixin):
    def dispatch_request(self):
        ctx = {}
        ctx['page'] = self.query(ExternalObject).options(joinedload(ExternalObject.attributes)).paginate()

        return render_template('objects/list.html', **ctx)


class ShowObjectView(View, DbMixin):
    def dispatch_request(self, id):
        ctx = {}
        ctx['object'] = self.query(ExternalObject).options(joinedload(ExternalObject.attributes)).get_or_404(id)

        return render_template('objects/show.html', **ctx)
