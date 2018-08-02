from flask import render_template, request
from flask.views import View
from sqlalchemy.orm import joinedload, undefer

from matcher.mixins import DbMixin
from matcher.scheme.enums import ExternalObjectType
from matcher.scheme.object import ExternalObject, ObjectLink
from matcher.scheme.platform import Platform, Scrap, Session

from ..forms.scraps import EditScrapForm, ScrapListFilter

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
        ctx['filter_form'] = form
        ctx['page'] = query.paginate()

        return render_template('scraps/list.html', **ctx)


class ShowScrapView(View, DbMixin):
    def dispatch_request(self, id):
        scrap = self.query(Scrap).options(joinedload(Scrap.platform),
                                          joinedload(Scrap.sessions)).get_or_404(id)

        formdata = request.form if request.method == 'POST' else None
        form = EditScrapForm(formdata=formdata, obj=scrap)
        form.sessions.query = self.query(Session)

        if form.validate():
            form.populate_obj(scrap)
            self.session.add(scrap)
            self.session.commit()

        ctx = {}
        ctx['scrap'] = scrap
        ctx['form'] = form
        ctx['objects'] = self.query(ExternalObject).\
            options(joinedload(ExternalObject.attributes),
                    undefer(ExternalObject.links_count)).\
            join(ExternalObject.links).\
            join(ObjectLink.scraps).\
            filter(Scrap.id == scrap.id,
                   ExternalObject.type != ExternalObjectType.PERSON)

        return render_template('scraps/show.html', **ctx)
