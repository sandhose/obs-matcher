from itertools import chain

from pytest import raises

from matcher.scheme import ExportTemplate, ExternalObject, ObjectLink, Platform
from matcher.scheme.enums import ExportRowType, ExternalObjectType
from matcher.scheme.views import AttributesView


class TestExportTemplate(object):
    def test_need(self):
        template = ExportTemplate()

        template.fields = []
        assert template.needs == set(), "should have no need"

        template.fields = [{"value": "'foo'"}, {"value": "3 + 2"}]
        assert template.needs == set(), "should have no need"

        template.fields = [{"value": "foo"}, {"value": "bar + baz"}]
        assert template.needs == set(["foo", "bar", "baz"]), "should extract the needs"

        template.fields = [{"value": "foo"}, {"value": "bar + foo"}, {"value": "bar"}]
        assert template.needs == set(["foo", "bar"]), "should deduplicate the needs"

    def test_links(self):
        template = ExportTemplate()

        template.fields = []
        assert template.links == [], "should have no link"

        template.fields = [{"value": "foo"}]
        assert template.links == [], "should have no link"

        template.fields = [{"value": "links['foo'] + bar"}]
        assert template.links == ["foo"], "should extract the link"

        template.fields = [{"value": "mainlinks + linksbar + mainlinks['bar']"}]
        assert template.links == [], "should not be fooled by value including `links`"

        template.fields = [{"value": "links['foo']"}, {"value": "links['bar'] + links['foo']"}]
        assert template.links == ["bar", "foo"], "should dedupe links"

        template.fields = [{"value": "links['bar'] + links['foo']"}]
        tmp_links = template.links
        template.fields = [{"value": "links['foo'] + links['bar']"}]
        assert template.links == tmp_links, "order should stay the same"

    def test_header(self):
        template = ExportTemplate()

        template.fields = []
        assert template.header == "", "header should be empty"

        template.fields = [{"name": "foo"}, {"name": "bar"}]
        assert template.header == "foo\tbar", "header should be correctly generated"

        template.fields = [{}, {}, {}]
        assert template.header == "\t\t", "empty column headers should stay as such"

        template.fields = [{"name": "foo\tbar"}, {"name": '"baz"'}]
        assert template.header == "\"foo\\\tbar\"\t\"\\\"baz\\\"\"", "column should be quoted"

    def test_to_context(self):
        platform = Platform()
        external_object = ExternalObject()
        object_link = ObjectLink(external_object=external_object,
                                 platform=platform,
                                 external_id='foo')

        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[]
        ).to_context((external_object, ))
        assert context == {
            'external_object': external_object,
            'links': {}
        }

        # OBJECT_LINK rows should have the `current` link
        context = ExportTemplate(
            row_type=ExportRowType.OBJECT_LINK,
            fields=[]
        ).to_context((object_link, external_object, ))
        assert context == {
            'external_object': external_object,
            'links': {'current': 'foo'}
        }

        # OBJECT_LINK rows should be able to request the platform
        context = ExportTemplate(
            row_type=ExportRowType.OBJECT_LINK,
            fields=[{"value": "platform.name"}]
        ).to_context((object_link, external_object, ))

        assert context == {
            'external_object': external_object,
            'platform': platform,
            'links': {'current': 'foo'}
        }

        # EXTERNAL_OBJECT rows shall not ask for the platform
        with raises(Exception, message="Platform can't be queried when the row_type is EXTERNAL_OBJECT"):
            context = ExportTemplate(
                row_type=ExportRowType.PLATFORM,
                fields=[{"value": "platform.name"}]
            ).to_context((object_link, external_object, ))

        # Requested links should be there
        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[{"value": "links['foo']"}]
        ).to_context((external_object, 'bar', ))
        assert context == {
            'external_object': external_object,
            'links': {'foo': 'bar'}
        }

        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[{"value": "attributes.country | join(',')"}]
        ).to_context((external_object, ))
        assert 'attributes' in context
        assert context['attributes'].view != external_object.attributes, \
            "an empty AttributesView should be associated with the attributes"
        assert context['attributes'].titles == [], "attributes should fall back to empty lists"

        with raises(AttributeError):
            # Invalid attributes should fail
            context['attributes'].foo

        # Let's set some attributes
        external_object.attributes = AttributesView(titles=['foo'])
        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[{"value": "attributes.titles[0]"}]
        ).to_context((external_object, ))
        assert 'attributes' in context
        assert context['attributes'].view == external_object.attributes, "the AttributesView should be associated"
        assert context['attributes'].titles == ["foo"], "attributes that are set should work"
        assert context['attributes'].genres == [], "attributes that are not set should fall back to empty arrays"

        with raises(AttributeError):
            # Invalid attributes should fail
            context['attributes'].foo

        # Let's set some attributes
        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[{"value": "zones.EUROBS"}]
        ).to_context((external_object, ))
        assert 'zones' in context, "the context should include zone informations"
        assert 'FR' in context['zones'].EUROBS, "the zones should have some data in them"

    def test_compile_template(self):
        assert ExportTemplate(fields=[]).template == ""
        assert ExportTemplate(fields=[{"value": "foo"}, {"value": "bar"}]).template \
            == "{{ (foo) | quote }}\t{{ (bar) | quote }}"

        template = ExportTemplate(fields=[{"value": "foo"}, {"value": "bar"}]).compile_template()
        assert template({'foo': 'hello', 'bar': 'world'}) \
            == 'hello\tworld', "the compiled template should be a callable"

    def test_valid_template(self):
        assert ExportTemplate(fields=[]).valid_template
        assert ExportTemplate(fields=[{"value": "platform.name"}],
                              row_type=ExportRowType.OBJECT_LINK).valid_template
        assert not ExportTemplate(fields=[{"value": "platform.name"}],
                                  row_type=ExportRowType.EXTERNAL_OBJECT).valid_template
        assert ExportTemplate(fields=[{"value": "external_object.id"},
                                      {"value": "attributes.titles[0]"}],
                              row_type=ExportRowType.EXTERNAL_OBJECT).valid_template

    def test_row_query(self, session):
        platforms = [Platform(slug='platform-' + str(i), name='Platform ' + str(i)) for i in range(4)]
        series = [ExternalObject(type=ExternalObjectType.SERIES) for _ in range(2)]
        movies = [ExternalObject(type=ExternalObjectType.MOVIE) for _ in range(3)]

        links = [ObjectLink(platform=p, external_object=eo, external_id='link-{}-{}-{}'.format(p.slug, eo.type, index))
                 for (index, eo) in chain(enumerate(series), enumerate(movies))
                 for p in platforms]

        session.add_all(platforms + movies + series + links)
        session.commit()

        # Start by checking the row count matches
        assert ExportTemplate(
            external_object_type=ExternalObjectType.MOVIE,
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[]
        ).get_row_query(session=session).count() == len(movies)

        assert ExportTemplate(
            external_object_type=ExternalObjectType.SERIES,
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[]
        ).get_row_query(session=session).count() == len(series)

        assert ExportTemplate(
            external_object_type=ExternalObjectType.MOVIE,
            row_type=ExportRowType.OBJECT_LINK,
            fields=[]
        ).get_row_query(session=session).count() == len(movies) * len(platforms)

        assert ExportTemplate(
            external_object_type=ExternalObjectType.SERIES,
            row_type=ExportRowType.OBJECT_LINK,
            fields=[]
        ).get_row_query(session=session).count() == len(series) * len(platforms)

        # Results are wrapped in sets because the order is not stable
        assert set(ExportTemplate(
            external_object_type=ExternalObjectType.SERIES,
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[
                {'value': 'links["platform-1"]'},
                {'value': 'links["platform-3"]'},
            ]
        ).get_row_query(session=session)) == set([
            (series[0], 'link-platform-1-series-0', 'link-platform-3-series-0'),
            (series[1], 'link-platform-1-series-1', 'link-platform-3-series-1'),
        ])

        # Results are wrapped in sets because the order is not stable
        assert set(ExportTemplate(
            external_object_type=ExternalObjectType.SERIES,
            row_type=ExportRowType.OBJECT_LINK,
            fields=[
                {'value': 'attributes'},
                {'value': 'platform'},
                {'value': 'links["platform-0"]'},
                {'value': 'links["platform-2"]'},
            ]
        ).get_row_query(session=session)) == set([
            (links[0], series[0], 'link-platform-0-series-0', 'link-platform-2-series-0'),
            (links[1], series[0], 'link-platform-0-series-0', 'link-platform-2-series-0'),
            (links[2], series[0], 'link-platform-0-series-0', 'link-platform-2-series-0'),
            (links[3], series[0], 'link-platform-0-series-0', 'link-platform-2-series-0'),
            (links[4], series[1], 'link-platform-0-series-1', 'link-platform-2-series-1'),
            (links[5], series[1], 'link-platform-0-series-1', 'link-platform-2-series-1'),
            (links[6], series[1], 'link-platform-0-series-1', 'link-platform-2-series-1'),
            (links[7], series[1], 'link-platform-0-series-1', 'link-platform-2-series-1')
        ])

        # Checking the generated contexts
        template = ExportTemplate(
            external_object_type=ExternalObjectType.SERIES,
            row_type=ExportRowType.OBJECT_LINK,
            fields=[
                {'value': 'platform'},
                {'value': 'links["platform-0"]'},
            ]
        )

        # dicts are not hashable, we need to sort manually
        def sort_key(d):
            return d['links']['current']

        rows = list(template.to_context(row) for row in template.get_row_query(session=session))
        expected = [
            {'external_object': series[0], 'platform': platforms[0],
             'links': {'current': links[0].external_id, 'platform-0': 'link-platform-0-series-0'}},
            {'external_object': series[0], 'platform': platforms[1],
             'links': {'current': links[1].external_id, 'platform-0': 'link-platform-0-series-0'}},
            {'external_object': series[0], 'platform': platforms[2],
             'links': {'current': links[2].external_id, 'platform-0': 'link-platform-0-series-0'}},
            {'external_object': series[0], 'platform': platforms[3],
             'links': {'current': links[3].external_id, 'platform-0': 'link-platform-0-series-0'}},
            {'external_object': series[1], 'platform': platforms[0],
             'links': {'current': links[4].external_id, 'platform-0': 'link-platform-0-series-1'}},
            {'external_object': series[1], 'platform': platforms[1],
             'links': {'current': links[5].external_id, 'platform-0': 'link-platform-0-series-1'}},
            {'external_object': series[1], 'platform': platforms[2],
             'links': {'current': links[6].external_id, 'platform-0': 'link-platform-0-series-1'}},
            {'external_object': series[1], 'platform': platforms[3],
             'links': {'current': links[7].external_id, 'platform-0': 'link-platform-0-series-1'}},
        ]

        assert sorted(rows, key=sort_key) == sorted(expected, key=sort_key)
