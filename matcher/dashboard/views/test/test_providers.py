from matcher.scheme.platform import Platform
from matcher.scheme.provider import Provider, ProviderPlatform
from matcher.utils import captured_templates


class TestProviderListView(object):
    def test_list(self, client, app, session):
        platform = Platform(name="Platform")
        provider = Provider(name="Provider", slug="provider")
        session.add(platform, provider)
        session.add(ProviderPlatform(platform=platform, provider=provider))
        session.commit()

        with captured_templates(app) as templates:
            rv = client.get("/providers/")
            assert rv.status_code == 200
            assert len(templates) == 1
            template, context = templates[0]

            assert template.name == "providers/list.html"
            assert "page" in context
            assert "filter_form" in context
            assert "ordering" in context

            assert len(context["page"].items) == 1
            assert context["page"].items[0] == provider
            assert len(context["page"].items[0].platforms) == 1
            assert context["page"].items[0].platforms[0] == platform

            assert context["ordering"] is None
