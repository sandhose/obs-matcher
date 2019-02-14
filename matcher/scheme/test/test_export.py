from itertools import chain

from jinja2.exceptions import UndefinedError
from pytest import raises

from matcher.scheme import (
    Episode,
    ExportFactory,
    ExportFile,
    ExportTemplate,
    ExternalObject,
    ImportFile,
    ObjectLink,
    Platform,
    PlatformGroup,
    Scrap,
    Session,
    Value,
    ValueSource,
)
from matcher.scheme.enums import (
    ExportFactoryIterator,
    ExportFileStatus,
    ExportRowType,
    ExternalObjectType,
    ImportFileStatus,
    PlatformType,
    ValueType,
)
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

        template.fields = [
            {"value": "links['foo']"},
            {"value": "links['bar'] + links['foo']"},
        ]
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
        assert template.header == '"foo\tbar"\t"""baz"""', "column should be quoted"

    def test_to_context(self):
        platform = Platform()
        external_object = ExternalObject()
        object_link = ObjectLink(
            external_object=external_object, platform=platform, external_id="foo"
        )

        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT, fields=[]
        ).to_context((external_object,))
        assert context == {"external_object": external_object, "links": {}}

        # OBJECT_LINK rows should have the `current` link
        context = ExportTemplate(
            row_type=ExportRowType.OBJECT_LINK, fields=[]
        ).to_context((object_link, external_object))
        assert context == {
            "external_object": external_object,
            "links": {"current": "foo"},
        }

        # OBJECT_LINK rows should be able to request the platform
        context = ExportTemplate(
            row_type=ExportRowType.OBJECT_LINK, fields=[{"value": "platform.name"}]
        ).to_context((object_link, external_object))

        assert context == {
            "external_object": external_object,
            "platform": platform,
            "links": {"current": "foo"},
        }

        # EXTERNAL_OBJECT rows shall not ask for the platform
        with raises(
            Exception,
            message="Platform can't be queried when the row_type is EXTERNAL_OBJECT",
        ):
            context = ExportTemplate(
                row_type=ExportRowType.PLATFORM, fields=[{"value": "platform.name"}]
            ).to_context((object_link, external_object))

        # Requested links should be there
        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT, fields=[{"value": "links['foo']"}]
        ).to_context((external_object, "bar"))
        assert context == {"external_object": external_object, "links": {"foo": "bar"}}

        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[{"value": "attributes.country | join(',')"}],
        ).to_context((external_object,))
        assert "attributes" in context
        assert (
            context["attributes"].view != external_object.attributes
        ), "an empty AttributesView should be associated with the attributes"
        assert (
            context["attributes"].titles == []
        ), "attributes should fall back to empty lists"

        with raises(AttributeError):
            # Invalid attributes should fail
            context["attributes"].foo

        # Let's set some attributes
        external_object.attributes = AttributesView(titles=["foo"])
        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[{"value": "attributes.titles[0]"}],
        ).to_context((external_object,))
        assert "attributes" in context
        assert (
            context["attributes"].view == external_object.attributes
        ), "the AttributesView should be associated"
        assert context["attributes"].titles == [
            "foo"
        ], "attributes that are set should work"
        assert (
            context["attributes"].genres == []
        ), "attributes that are not set should fall back to empty arrays"

        with raises(AttributeError):
            # Invalid attributes should fail
            context["attributes"].foo

        # Let's set some attributes
        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT, fields=[{"value": "zones.EUROBS"}]
        ).to_context((external_object,))
        assert "zones" in context, "the context should include zone informations"
        assert (
            "FR" in context["zones"].EUROBS
        ), "the zones should have some data in them"

        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[{"value": "platform_countries"}],
        ).to_context((external_object, ["FR", "GB"]))
        assert (
            "platform_countries" in context
        ), "the context should include platform countries"
        assert context["platform_countries"] == ["FR", "GB"]

        context = ExportTemplate(
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[{"value": "platform_countries"}, {"value": "platform_names"}],
        ).to_context((external_object, ["FR"], ["Platform 1", "Platform 2"]))
        assert (
            "platform_countries" in context
        ), "the context should include platform countries"
        assert "platform_names" in context, "the context should include platform names"
        assert context["platform_countries"] == ["FR"]
        assert context["platform_names"] == ["Platform 1", "Platform 2"]

    def test_compile_template(self):
        assert ExportTemplate(fields=[]).template == ""
        assert (
            ExportTemplate(fields=[{"value": "foo"}, {"value": "bar"}]).template
            == "{{ (foo) | quote }}\t{{ (bar) | quote }}"
        )

        template = ExportTemplate(
            fields=[{"value": "foo"}, {"value": "bar"}]
        ).compile_template()
        assert (
            template({"foo": "hello", "bar": "world"}) == "hello\tworld"
        ), "the compiled template should be a callable"

    def test_valid_template(self):
        assert ExportTemplate(fields=[]).valid_template
        assert ExportTemplate(
            fields=[{"value": "platform.name"}], row_type=ExportRowType.OBJECT_LINK
        ).valid_template
        assert not ExportTemplate(
            fields=[{"value": "platform.name"}], row_type=ExportRowType.EXTERNAL_OBJECT
        ).valid_template
        assert ExportTemplate(
            fields=[{"value": "external_object.id"}, {"value": "attributes.titles[0]"}],
            row_type=ExportRowType.EXTERNAL_OBJECT,
        ).valid_template
        assert not ExportTemplate(
            fields=[{"value": "episodes_count"}],
            external_object_type=ExternalObjectType.MOVIE,
        ).valid_template
        assert ExportTemplate(
            fields=[{"value": "episodes_count"}],
            external_object_type=ExternalObjectType.SERIES,
        ).valid_template

    def test_row_query(self, session):
        platforms = [
            Platform(slug="platform-" + str(i), name="Platform " + str(i))
            for i in range(4)
        ]
        platforms[0].country = "FR"
        platforms[1].country = "FR"
        platforms[2].country = "DE"
        series = [ExternalObject(type=ExternalObjectType.SERIES) for _ in range(2)]
        movies = [ExternalObject(type=ExternalObjectType.MOVIE) for _ in range(3)]

        episodes = []
        episodes_rel = []
        for s in series:
            for season in range(3):
                for episode in range(10):
                    eo = ExternalObject(type=ExternalObjectType.EPISODE)
                    rel = Episode(
                        external_object=eo, series=s, episode=episode, season=season
                    )
                    episodes.append(eo)
                    episodes_rel.append(rel)

        links = [
            ObjectLink(
                platform=p,
                external_object=eo,
                external_id="link-{}-{}-{}".format(p.slug, eo.type, index),
            )
            for (index, eo) in chain(
                enumerate(series), enumerate(movies), enumerate(episodes)
            )
            for p in platforms
        ]

        session.add_all(platforms + movies + series + links + episodes_rel + episodes)
        session.commit()

        # Start by checking the row count matches
        assert ExportTemplate(
            external_object_type=ExternalObjectType.MOVIE,
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[],
        ).get_row_query(session=session).count() == len(movies)

        assert ExportTemplate(
            external_object_type=ExternalObjectType.SERIES,
            row_type=ExportRowType.EXTERNAL_OBJECT,
            fields=[],
        ).get_row_query(session=session).count() == len(series)

        assert ExportTemplate(
            external_object_type=ExternalObjectType.MOVIE,
            row_type=ExportRowType.OBJECT_LINK,
            fields=[],
        ).get_row_query(session=session).count() == len(movies) * len(platforms)

        assert ExportTemplate(
            external_object_type=ExternalObjectType.SERIES,
            row_type=ExportRowType.OBJECT_LINK,
            fields=[],
        ).get_row_query(session=session).count() == len(series) * len(platforms)

        # Results are wrapped in sets because the order is not stable
        assert set(
            ExportTemplate(
                external_object_type=ExternalObjectType.SERIES,
                row_type=ExportRowType.EXTERNAL_OBJECT,
                fields=[
                    {"value": 'links["platform-1"]'},
                    {"value": 'links["platform-3"]'},
                ],
            ).get_row_query(session=session)
        ) == set(
            [
                (series[0], "link-platform-1-series-0", "link-platform-3-series-0"),
                (series[1], "link-platform-1-series-1", "link-platform-3-series-1"),
            ]
        )

        # Export platform names and countries
        rows = list(
            sorted(
                ExportTemplate(
                    external_object_type=ExternalObjectType.SERIES,
                    row_type=ExportRowType.EXTERNAL_OBJECT,
                    fields=[
                        {"value": "platform_names"},
                        {"value": "platform_countries"},
                    ],
                ).get_row_query(session=session),
                key=lambda r: r[0].id,
            )
        )

        assert rows[0][0] == series[0]
        assert set(rows[0][1]) == set(["FR", "DE", None])
        assert sorted(rows[0][2]) == sorted(p.name for p in platforms)
        assert rows[1][0] == series[1]
        assert set(rows[1][1]) == set(["FR", "DE", None])
        assert sorted(rows[1][2]) == sorted(p.name for p in platforms)

        # Export episodes and seasons count
        assert set(
            ExportTemplate(
                external_object_type=ExternalObjectType.SERIES,
                row_type=ExportRowType.EXTERNAL_OBJECT,
                fields=[{"value": "seasons_count"}, {"value": "episodes_count"}],
            ).get_row_query(session=session)
        ) == set([(series[0], 3, 30), (series[1], 3, 30)])

        # Results are wrapped in sets because the order is not stable
        assert set(
            ExportTemplate(
                external_object_type=ExternalObjectType.SERIES,
                row_type=ExportRowType.OBJECT_LINK,
                fields=[
                    {"value": "attributes"},
                    {"value": "platform"},
                    {"value": 'links["platform-0"]'},
                    {"value": 'links["platform-2"]'},
                ],
            ).get_row_query(session=session)
        ) == set(
            [
                (
                    links[0],
                    series[0],
                    "link-platform-0-series-0",
                    "link-platform-2-series-0",
                ),
                (
                    links[1],
                    series[0],
                    "link-platform-0-series-0",
                    "link-platform-2-series-0",
                ),
                (
                    links[2],
                    series[0],
                    "link-platform-0-series-0",
                    "link-platform-2-series-0",
                ),
                (
                    links[3],
                    series[0],
                    "link-platform-0-series-0",
                    "link-platform-2-series-0",
                ),
                (
                    links[4],
                    series[1],
                    "link-platform-0-series-1",
                    "link-platform-2-series-1",
                ),
                (
                    links[5],
                    series[1],
                    "link-platform-0-series-1",
                    "link-platform-2-series-1",
                ),
                (
                    links[6],
                    series[1],
                    "link-platform-0-series-1",
                    "link-platform-2-series-1",
                ),
                (
                    links[7],
                    series[1],
                    "link-platform-0-series-1",
                    "link-platform-2-series-1",
                ),
            ]
        )

        # Checking the generated contexts
        template = ExportTemplate(
            external_object_type=ExternalObjectType.SERIES,
            row_type=ExportRowType.OBJECT_LINK,
            fields=[{"value": "platform"}, {"value": 'links["platform-0"]'}],
        )

        # dicts are not hashable, we need to sort manually
        def sort_key(d):
            return d["links"]["current"]

        rows = list(
            template.to_context(row) for row in template.get_row_query(session=session)
        )
        expected = [
            {
                "external_object": series[0],
                "platform": platforms[0],
                "links": {
                    "current": links[0].external_id,
                    "platform-0": "link-platform-0-series-0",
                },
            },
            {
                "external_object": series[0],
                "platform": platforms[1],
                "links": {
                    "current": links[1].external_id,
                    "platform-0": "link-platform-0-series-0",
                },
            },
            {
                "external_object": series[0],
                "platform": platforms[2],
                "links": {
                    "current": links[2].external_id,
                    "platform-0": "link-platform-0-series-0",
                },
            },
            {
                "external_object": series[0],
                "platform": platforms[3],
                "links": {
                    "current": links[3].external_id,
                    "platform-0": "link-platform-0-series-0",
                },
            },
            {
                "external_object": series[1],
                "platform": platforms[0],
                "links": {
                    "current": links[4].external_id,
                    "platform-0": "link-platform-0-series-1",
                },
            },
            {
                "external_object": series[1],
                "platform": platforms[1],
                "links": {
                    "current": links[5].external_id,
                    "platform-0": "link-platform-0-series-1",
                },
            },
            {
                "external_object": series[1],
                "platform": platforms[2],
                "links": {
                    "current": links[6].external_id,
                    "platform-0": "link-platform-0-series-1",
                },
            },
            {
                "external_object": series[1],
                "platform": platforms[3],
                "links": {
                    "current": links[7].external_id,
                    "platform-0": "link-platform-0-series-1",
                },
            },
        ]

        assert sorted(rows, key=sort_key) == sorted(expected, key=sort_key)


class TestExportFactory(object):
    def test_iterate(self, session):
        platforms = [
            Platform(name="TVOD FR", type=PlatformType.TVOD, country="FR"),
            Platform(name="TVOD GB", type=PlatformType.TVOD, country="GB"),
            Platform(name="SVOD FR", type=PlatformType.SVOD, country="FR"),
            Platform(name="SVOD IT", type=PlatformType.SVOD, country="IT"),
            Platform(name="SVOD DE", type=PlatformType.SVOD, country="DE"),
            Platform(name="SVOD Global", type=PlatformType.GLOBAL),
            Platform(
                name="Ignored",
                type=PlatformType.TVOD,
                ignore_in_exports=True,
                country="RU",
            ),
            Platform(name="Info", type=PlatformType.INFO),
            Platform(name="No group ES", type=PlatformType.TVOD, country="ES"),
        ]

        groups = [
            PlatformGroup(name="Group TVOD", platforms=[platforms[0], platforms[1]]),
            PlatformGroup(
                name="Group SVOD",
                platforms=[platforms[2], platforms[3], platforms[4], platforms[5]],
            ),
        ]

        session.add_all(platforms + groups)
        session.commit()

        # FIXME: the order might not be stable
        assert list(
            ExportFactory(iterator=ExportFactoryIterator.PLATFORMS).iterate(
                session=session
            )
        ) == [
            {"platform": platforms[0]},  # TVOD FR
            {"platform": platforms[1]},  # TVOD GB
            {"platform": platforms[2]},  # SVOD FR
            {"platform": platforms[3]},  # SVOD IT
            {"platform": platforms[4]},  # SVOD DE
            {"platform": platforms[-1]},  # No group ES
        ], "the PLATFORMS iterator should yield each TVOD/SVOD and non-ignored platform once"

        assert list(
            ExportFactory(iterator=ExportFactoryIterator.GROUPS).iterate(
                session=session
            )
        ) == [
            {"group": groups[0]},  # Group TVOD
            {"group": groups[1]},  # Group SVOD
        ], "the GROUPS iterator should yield each group once"

        # FIXME: this *might* be ordered alphabetically by country because of the way GROUP BY works
        assert list(
            ExportFactory(iterator=ExportFactoryIterator.COUNTRIES).iterate(
                session=session
            )
        ) == [
            {"country": "DE"},
            {"country": "ES"},
            {"country": "FR"},
            {"country": "GB"},
            {"country": "IT"},
        ], "the COUNTRIES iterator should yield a country list without duplicate"

        assert list(ExportFactory(iterator=None).iterate(session=session)) == [
            {}
        ], "the 'None' iterator should yield one empty context"

    def test_compile_filters_template(self):
        template = ExportFactory(filters_template={}).compile_filters_template()
        assert template({}) == {}

        template = ExportFactory(
            filters_template={"foo": "bar"}
        ).compile_filters_template()
        assert template({}) == {"foo": "bar"}

        template = ExportFactory(
            filters_template={"foo": "{{ bar }}"}
        ).compile_filters_template()
        assert template({"bar": "baz"}) == {"foo": "baz"}
        assert template({"bar": "foobar"}) == {"foo": "foobar"}

        with raises(UndefinedError):
            template({})

        template = ExportFactory(
            filters_template={
                "foo": "{{ foo }}",
                "bar": "{{ bar | upper }}",
                "baz": "const",
            }
        ).compile_filters_template()
        assert template({"foo": 42, "bar": "foobar"}) == {
            "foo": "42",
            "bar": "FOOBAR",
            "baz": "const",
        }

    def test_compile_path_template(self):
        template = ExportFactory(file_path_template="foo_bar").compile_path_template()
        assert template({}) == "foo_bar"

        template = ExportFactory(
            file_path_template="foo_{{ bar }}"
        ).compile_path_template()
        assert template({"bar": "baz"}) == "foo_baz"

        with raises(UndefinedError):
            template({})

        template = ExportFactory(
            file_path_template="foo_{{ bar | pathify }}"
        ).compile_path_template()
        assert template({"bar": "Bar à chat"}) == "foo_bar_a_chat"

    def test_generate(self, session):
        platforms = [
            Platform(name="Platform 1", type=PlatformType.TVOD, country="FR"),
            Platform(name="Platform 2", type=PlatformType.SVOD, country="GB"),
        ]

        group = PlatformGroup(name="Group Name", platforms=platforms)
        session.add_all(platforms + [group])
        session.commit()

        scrap_session = Session()
        template = ExportTemplate()
        factory = ExportFactory(
            template=template,
            iterator=ExportFactoryIterator.PLATFORMS,
            filters_template={"platform.id": "{{ platform.id }}"},
            file_path_template=(
                "{{ platform.type | upper }}_"
                "{{ platform.country | lower }}_"
                "{{ platform.name | pathify }}"
            ),
        )
        files = list(factory.generate(scrap_session=scrap_session, session=session))

        assert len(files) == len(platforms)
        assert all(file.factory == factory for file in files)
        assert all(file.template == template for file in files)
        assert all(file.session == scrap_session for file in files)
        assert files[0].path == "TVOD_fr_platform_1"
        assert files[1].path == "SVOD_gb_platform_2"
        assert files[0].filters == {"platform.id": str(platforms[0].id)}
        assert files[1].filters == {"platform.id": str(platforms[1].id)}


class TestExportFile(object):
    def test_count_links(self, session):
        object_session = Session(name="test")
        import_file = ImportFile(
            sessions=[object_session],
            status=ImportFileStatus.DONE,
            filename="foo.csv",
            fields={},
        )
        external_object = ExternalObject(type=ExternalObjectType.MOVIE)
        empty_platform = Platform(name="empty", type=PlatformType.TVOD)
        linked_platform = Platform(name="linked", type=PlatformType.TVOD)
        link = ObjectLink(
            external_object=external_object,
            platform=linked_platform,
            external_id="link",
            imports=[import_file],
        )
        session.add_all(
            [external_object, empty_platform, linked_platform, link, import_file]
        )
        session.commit()

        template = ExportTemplate(
            external_object_type=ExternalObjectType.MOVIE,
            row_type=ExportRowType.OBJECT_LINK,
            fields={},
        )

        assert (
            ExportFile(
                template=template,
                session=object_session,
                status=ExportFileStatus.DONE,
                path="foo.csv",
                filters={},
            ).count_links(session=session)
            == 1
        )
        assert (
            ExportFile(
                template=template,
                session=object_session,
                status=ExportFileStatus.DONE,
                path="foo.csv",
                filters={"platform.id": str(linked_platform.id)},
            ).count_links(session=session)
            == 1
        )
        assert (
            ExportFile(
                template=template,
                session=object_session,
                status=ExportFileStatus.DONE,
                path="foo.csv",
                filters={"platform.id": str(empty_platform.id)},
            ).count_links(session=session)
            == 0
        )

    def test_filtered_query(self, session):
        platforms = [
            Platform(name="TVOD FR", type=PlatformType.TVOD, country="FR"),
            Platform(name="TVOD GB", type=PlatformType.TVOD, country="GB"),
            Platform(name="SVOD FR", type=PlatformType.SVOD, country="FR"),
            Platform(name="SVOD IT", type=PlatformType.SVOD, country="IT"),
            Platform(name="SVOD DE", type=PlatformType.SVOD, country="DE"),
        ]

        object_session = Session(name="test")
        scrap = Scrap(platform=platforms[0], sessions=[object_session])

        groups = [
            PlatformGroup(name="Group TVOD", platforms=[platforms[0], platforms[1]]),
            PlatformGroup(
                name="Group SVOD", platforms=[platforms[2], platforms[3], platforms[4]]
            ),
        ]

        objects = [
            ExternalObject(
                type=ExternalObjectType.MOVIE,
                links=[
                    ObjectLink(
                        platform=platforms[0], external_id="tvod-fr-a", scraps=[scrap]
                    ),
                    ObjectLink(
                        platform=platforms[1], external_id="tvod-gb-a", scraps=[scrap]
                    ),
                ],
                values=[
                    Value(
                        type=ValueType.TITLE,
                        text="A",
                        sources=[ValueSource(platform=platforms[0])],
                    ),
                    Value(
                        type=ValueType.COUNTRY,
                        text="US",
                        sources=[
                            ValueSource(platform=platforms[0]),
                            ValueSource(platform=platforms[1]),
                        ],
                    ),
                    Value(
                        type=ValueType.COUNTRY,
                        text="GB",
                        sources=[ValueSource(platform=platforms[0])],
                    ),
                ],
            ),
            ExternalObject(
                type=ExternalObjectType.MOVIE,
                links=[
                    ObjectLink(
                        platform=platforms[0], external_id="tvod-fr-b", scraps=[scrap]
                    ),
                    ObjectLink(
                        platform=platforms[3], external_id="svod-it-b", scraps=[scrap]
                    ),
                    ObjectLink(
                        platform=platforms[4], external_id="svod-de-b", scraps=[scrap]
                    ),
                ],
                values=[
                    Value(
                        type=ValueType.TITLE,
                        text="B",
                        sources=[ValueSource(platform=platforms[0])],
                    )
                ],
            ),
        ]

        # This is used to freeze the links orders
        links = objects[0].links + objects[1].links

        session.add_all(platforms + groups + objects + [scrap])
        session.commit()

        template = ExportTemplate(
            fields=[{"value": 'links["{}"]'.format(platforms[0].slug)}],
            external_object_type=ExternalObjectType.MOVIE,
        )

        file = ExportFile(
            template=template,
            session=object_session,
            status=ExportFileStatus.SCHEDULED,
            path="foo.csv",
        )

        template.row_type = ExportRowType.OBJECT_LINK
        file.filters = {}
        assert set(file.get_filtered_query(session=session)) == set(
            [
                (links[0], objects[0], "tvod-fr-a"),
                (links[1], objects[0], "tvod-fr-a"),
                (links[2], objects[1], "tvod-fr-b"),
                (links[3], objects[1], "tvod-fr-b"),
                (links[4], objects[1], "tvod-fr-b"),
            ]
        )

        template.row_type = ExportRowType.EXTERNAL_OBJECT
        file.filters = {}
        assert set(file.get_filtered_query(session=session)) == set(
            [(objects[0], "tvod-fr-a"), (objects[1], "tvod-fr-b")]
        )

        template.row_type = ExportRowType.OBJECT_LINK
        file.filters = {"platform.group_id": str(groups[0].id)}
        assert set(file.get_filtered_query(session=session)) == set(
            [
                (links[0], objects[0], "tvod-fr-a"),
                (links[1], objects[0], "tvod-fr-a"),
                (links[2], objects[1], "tvod-fr-b"),
            ]
        )

        template.row_type = ExportRowType.EXTERNAL_OBJECT
        file.filters = {"platform.group_id": str(groups[1].id)}
        assert set(file.get_filtered_query(session=session)) == set(
            [(objects[1], "tvod-fr-b")]
        )

        template.row_type = ExportRowType.OBJECT_LINK
        file.filters = {"platform.country": "FR,IT"}
        assert set(file.get_filtered_query(session=session)) == set(
            [
                (links[0], objects[0], "tvod-fr-a"),
                (links[2], objects[1], "tvod-fr-b"),
                (links[3], objects[1], "tvod-fr-b"),
            ]
        )

        template.row_type = ExportRowType.OBJECT_LINK
        file.filters = {"platform.id": str(platforms[0].id)}
        assert set(file.get_filtered_query(session=session)) == set(
            [(links[0], objects[0], "tvod-fr-a"), (links[2], objects[1], "tvod-fr-b")]
        )
