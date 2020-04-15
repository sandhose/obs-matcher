from flask import render_template, request
from matcher.mixins import InjectedView
from matcher.scheme.enums import ExternalObjectType
from matcher.scheme.object import ExternalObject, ObjectLink
from matcher.scheme.platform import Platform, Scrap, Session, session_scrap
from matcher.utils import apply_ordering, parse_ordering
from sqlalchemy.orm import joinedload, undefer

from ..forms.scraps import EditScrapForm, ScrapListFilter

__all__ = ["ScrapListView", "ShowScrapView"]


class ScrapListView(InjectedView):
    def dispatch_request(self):
        form = ScrapListFilter(request.args)
        form.platforms.query = self.query(Platform)
        form.sessions.query = self.query(Session)

        query = self.query(Scrap).options(joinedload(Scrap.platform))

        ordering = parse_ordering(request.args.get("ordering", None, str))
        ordering_key, ordering_direction = (
            ordering if ordering != (None, None) else ("date", "desc")
        )
        query = apply_ordering(
            {"date": Scrap.date, None: Scrap.id},
            query,
            key=ordering_key,
            direction=ordering_direction,
        )

        if form.validate():
            if form.platforms.data:
                query = query.join(Platform).filter(
                    Platform.id.in_(p.id for p in form.platforms.data)
                )

            if form.status.data:
                query = query.filter(Scrap.status.in_(form.status.data))

            if form.sessions.data:
                query = query.join(
                    session_scrap, Scrap.id == session_scrap.c.scrap_id
                ).filter(
                    session_scrap.c.session_id.in_(s.id for s in form.sessions.data)
                )

        ctx = {}
        ctx["filter_form"] = form
        ctx["ordering"] = request.args.get("ordering", None, str)
        ctx["page"] = query.paginate()

        return render_template("scraps/list.html", **ctx)


class ShowScrapView(InjectedView):
    def dispatch_request(self, id):
        scrap = (
            self.query(Scrap)
            .options(joinedload(Scrap.platform), joinedload(Scrap.sessions))
            .get_or_404(id)
        )

        formdata = request.form if request.method == "POST" else None
        form = EditScrapForm(formdata=formdata, obj=scrap)
        form.sessions.query = self.query(Session)

        if form.validate():
            form.populate_obj(scrap)
            self.session.add(scrap)
            self.session.commit()

        ctx = {}
        ctx["scrap"] = scrap
        ctx["form"] = form
        ctx["objects"] = (
            self.query(ExternalObject)
            .options(
                joinedload(ExternalObject.attributes),
                undefer(ExternalObject.links_count),
            )
            .join(ExternalObject.links)
            .join(ObjectLink.scraps)
            .filter(
                Scrap.id == scrap.id, ExternalObject.type != ExternalObjectType.PERSON
            )
        )

        return render_template("scraps/show.html", **ctx)
