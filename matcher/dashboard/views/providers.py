from flask import abort, render_template, request
from flask.views import View
from sqlalchemy.orm import undefer

from matcher.mixins import DbMixin
from matcher.scheme.provider import Provider
from matcher.utils import apply_ordering, parse_ordering

from ..forms.providers import ProviderListFilter

__all__ = ["ProviderListView", "ShowProviderView"]


class ProviderListView(View, DbMixin):
    def dispatch_request(self):
        form = ProviderListFilter(request.args)

        query = self.query(Provider).options(
            undefer(Provider.import_count), undefer(Provider.platform_count)
        )

        ordering_key, ordering_direction = parse_ordering(
            request.args.get("ordering", None, str)
        )

        query = apply_ordering(
            {
                "name": Provider.name,
                "slug": Provider.slug,
                "platforms": Provider.platform_count,
                "imports": Provider.import_count,
                None: Provider.id,
            },
            query,
            key=ordering_key,
            direction=ordering_direction,
        )

        if form.validate():
            if form.search.data:
                query = query.filter(Provider.search_filter(form.search.data))

        ctx = {}
        ctx["ordering"] = request.args.get("ordering", None, str)
        ctx["filter_form"] = form
        ctx["page"] = query.paginate()

        return render_template("providers/list.html", **ctx)


class ShowProviderView(View, DbMixin):
    def dispatch_request(self, slug):
        provider = self.query(Provider).filter(Provider.slug == slug).first()

        if provider is None:
            abort(404)

        ctx = {}
        ctx["provider"] = provider

        return render_template("providers/show.html", **ctx)
