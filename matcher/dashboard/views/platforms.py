import datetime

from flask import abort, render_template, request
from sqlalchemy import func
from sqlalchemy.orm import joinedload, undefer

from matcher.mixins import InjectedView
from matcher.scheme.object import ExternalObject, ObjectLink
from matcher.scheme.platform import Platform, PlatformGroup, Scrap
from matcher.scheme.provider import Provider
from matcher.utils import apply_ordering, parse_ordering

from ..forms.platforms import PlatformListFilter

__all__ = ["PlatformListView", "ShowPlatformView"]


class PlatformListView(InjectedView):
    def dispatch_request(self):
        form = PlatformListFilter(request.args)
        form.country.query = (
            self.query(Platform.country)
            .group_by(Platform.country)
            .order_by(Platform.country)
        )
        form.group.query = self.query(PlatformGroup).order_by(PlatformGroup.name)
        form.provider.query = self.query(Provider).order_by(Provider.name)
        query = self.query(Platform).options(
            undefer(Platform.links_count), joinedload(Platform.group)
        )

        ordering = parse_ordering(request.args.get("ordering", None, str))
        ordering_key, ordering_direction = (
            ordering if ordering != (None, None) else ("name", "asc")
        )
        query = apply_ordering(
            {
                "name": Platform.name,
                "slug": Platform.slug,
                "country": Platform.country,
                "links": Platform.links_count,
                None: Platform.id,
            },
            query,
            key=ordering_key,
            direction=ordering_direction,
        )

        if form.validate():
            if form.search.data:
                query = query.filter(Platform.search_filter(form.search.data))

            if form.type.data:
                query = query.filter(Platform.type.in_(form.type.data))

            if form.country.data:
                query = query.filter(Platform.country.in_(form.country.data))

            if form.group.data:
                query = query.filter(
                    Platform.group_id.in_(group.id for group in form.group.data)
                )

            if form.provider.data:
                query = query.join(Platform.providers).filter(
                    Provider.id.in_(p.id for p in form.provider.data)
                )

        ctx = {}
        ctx["ordering"] = request.args.get("ordering", None, str)
        ctx["filter_form"] = form
        ctx["page"] = query.paginate()

        return render_template("platforms/list.html", **ctx)


class ShowPlatformView(InjectedView):
    def dispatch_request(self, slug):
        platform = self.query(Platform).filter(Platform.slug == slug).first()

        if platform is None:
            abort(404)

        ctx = {}
        ctx["platform"] = platform
        ctx["link_stats"] = {
            type_.name: count
            for (type_, count) in (
                self.query(ExternalObject.type, func.count(ExternalObject.id))
                .join(ObjectLink)
                .filter(ObjectLink.platform == platform)
                .group_by(ExternalObject.type)
            )
        }

        now = datetime.datetime.utcnow()

        def last_scraps(timedelta):
            return (
                self.query(Scrap)
                .filter(Scrap.date >= (now - timedelta))
                .filter(Scrap.platform == platform)
                .count()
            )

        ctx["recent_scraps_count"] = {
            "week": last_scraps(datetime.timedelta(weeks=1)),
            "month": last_scraps(datetime.timedelta(days=30)),
            "year": last_scraps(datetime.timedelta(days=365)),
        }

        ctx["objects_sample"] = (
            self.query(ExternalObject)
            .filter(
                ExternalObject.id.in_(
                    self.query(ObjectLink.external_object_id).filter(
                        ObjectLink.platform == platform
                    )
                )
            )
            .order_by(func.random())
        )

        return render_template("platforms/show.html", **ctx)
