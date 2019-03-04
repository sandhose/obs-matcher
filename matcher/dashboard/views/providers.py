from flask import abort, redirect, render_template, request, url_for
from flask.views import View
from sqlalchemy.orm import undefer

from matcher.mixins import DbMixin
from matcher.scheme.platform import Platform
from matcher.scheme.provider import Provider, ProviderPlatform
from matcher.utils import apply_ordering, parse_ordering

from ..forms.providers import EditProviderForm, NewProviderForm, ProviderListFilter

__all__ = [
    "ProviderListView",
    "ShowProviderView",
    "NewProviderView",
    "EditProviderView",
]


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


class EditProviderView(View, DbMixin):
    def dispatch_request(self, slug):
        provider = self.query(Provider).filter(Provider.slug == slug).first()

        if provider is None:
            abort(404)

        form = EditProviderForm(request.form, obj=provider)
        form.platform_to_add.query = self.query(Platform)

        if request.method == "POST" and form.validate():
            form.populate_obj(provider)

            for index, subform in enumerate(form.provider_platforms):
                if subform.delete.data:
                    provider.platforms.remove(
                        provider.provider_platforms[index].platform
                    )
                    break

            self.session.add(provider)
            self.session.commit()

            if form.add_platform.data:
                self.session.merge(
                    ProviderPlatform(
                        platform=form.platform_to_add.data, provider=provider
                    )
                )

                self.session.commit()

            self.session.expire(provider)

        form.process(obj=provider)
        form.platform_to_add.data = None

        ctx = {}
        ctx["provider"] = provider
        ctx["form"] = form

        return render_template("providers/edit.html", **ctx)


class NewProviderView(View, DbMixin):
    def dispatch_request(self):
        provider = Provider()
        form = NewProviderForm(request.form)
        form.populate_obj(provider)

        if request.method == "POST" and form.validate():
            self.session.add(provider)
            self.session.commit()
            return redirect(url_for(".show_provider", slug=provider.slug))

        ctx = {}
        ctx["form"] = form

        return render_template("providers/new.html", **ctx)
