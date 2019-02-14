from pytest import raises

from ..enums import ExternalObjectType, ImportFileStatus, ValueType
from ..import_ import ImportFile
from ..object import ExternalObject, ObjectLink
from ..platform import Platform
from ..value import Value, ValueSource


class TestImportFile(object):
    def test_map_fields(self):
        file = ImportFile(
            fields={
                "foo": "external_object_id",
                "bar": "attribute.title",
                "baz": "attribute_list.genres",
            }
        )

        assert file.map_fields(["col", "foo", "bar", "baz"]) == {
            "external_object_id": [1],
            "attribute": {"title": [2]},
            "attribute_list": {"genres": [3]},
            "link": {},
        }

        # Repeating fields
        file = ImportFile(fields={"foo": "external_object_id"})

        assert file.map_fields(["foo", "foo", "bar", "foo"]) == {
            "external_object_id": [0, 1, 3],
            "attribute": {},
            "attribute_list": {},
            "link": {},
        }

        # Repeating fields with args
        file = ImportFile(fields={"title": "attribute.title", "date": "attribute.date"})

        assert file.map_fields(["title", "title", "date", "date"]) == {
            "external_object_id": [],
            "attribute": {"title": [0, 1], "date": [2, 3]},
            "attribute_list": {},
            "link": {},
        }

        # Raises on invalid fields
        with raises(KeyError):
            ImportFile(fields={"foo": "foo"}).map_fields(["foo"])

        # Raises when the column was not found
        with raises(AssertionError):
            ImportFile(fields={"foo": "external_object_id"}).map_fields([])

        # Raises when no arg was given
        with raises(AssertionError):
            ImportFile(fields={"foo": "attribute"}).map_fields(["foo"])

    def test_process_row(self, session):
        f = ImportFile(
            filename="foo.csv", status=ImportFileStatus.PROCESSING, fields={}
        )
        p1 = Platform(name="Foo", slug="foo")
        p2 = Platform(name="Bar", slug="bar")

        # First (simple) case: merge two IDs
        obj1 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            values=[
                Value(
                    type=ValueType.TITLE,
                    text="Foo",
                    sources=[ValueSource(platform=p1, score_factor=1)],
                )
            ],
        )
        obj2 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            values=[
                Value(
                    type=ValueType.TITLE,
                    text="Bar",
                    sources=[ValueSource(platform=p2, score_factor=1)],
                )
            ],
        )

        session.add_all([p1, p2, obj1, obj2])
        session.commit()

        f.process_row(
            external_object_ids=[obj1.id, obj2.id],
            attributes=[],
            links=[],
            session=session,
        )
        session.commit()
        obj = session.query(ExternalObject).first()

        assert session.query(ExternalObject).count() == 1
        assert len(obj.values) == 2
        session.delete(obj)
        session.commit()

        # Links should be added
        obj = ExternalObject(type=ExternalObjectType.MOVIE)
        session.add(obj)
        session.commit()

        f.process_row(
            external_object_ids=[obj.id],
            attributes=[],
            links=[(p1, ["foo-0"])],
            session=session,
        )
        session.commit()

        assert len(obj.links) == 1
        assert obj.links[0].platform == p1
        assert obj.links[0].external_id == "foo-0"

        session.delete(obj)
        session.commit()

        # Testing here that values associated by a replaced link are being evicted
        obj = ExternalObject(
            type=ExternalObjectType.MOVIE,
            links=[ObjectLink(platform=p1, external_id="foo-1")],
            values=[
                Value(
                    type=ValueType.TITLE,
                    text="Foo",
                    sources=[ValueSource(platform=p1, score_factor=1)],
                ),
                Value(
                    type=ValueType.TITLE,
                    text="Bar",
                    sources=[ValueSource(platform=p2, score_factor=1)],
                ),
            ],
        )

        session.add(obj)
        session.commit()

        f.process_row(
            external_object_ids=[obj.id],
            attributes=[],
            links=[(p1, ["foo-2"])],
            session=session,
        )
        session.commit()

        assert len(obj.values) == 1
        assert len(obj.links) == 1
        assert obj.links[0].external_id == "foo-2"

        session.delete(obj)
        session.commit()

        # …but should stay if they have another source
        obj = ExternalObject(
            type=ExternalObjectType.MOVIE,
            links=[ObjectLink(platform=p1, external_id="foo-1")],
            values=[
                Value(
                    type=ValueType.TITLE,
                    text="Foo",
                    sources=[
                        ValueSource(platform=p1, score_factor=1),
                        ValueSource(platform=p2, score_factor=1),
                    ],
                )
            ],
        )

        session.add(obj)
        session.commit()

        f.process_row(
            external_object_ids=[obj.id],
            attributes=[],
            links=[(p1, ["foo-2"])],
            session=session,
        )
        session.commit()

        assert len(obj.values) == 1
        assert len(obj.values[0].sources) == 1

        session.delete(obj)
        session.commit()

        # Objects with the same ID should merge (and their attributes as well)
        obj1 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            values=[
                Value(
                    type=ValueType.TITLE,
                    text="Foo",
                    sources=[ValueSource(platform=p1, score_factor=1)],
                )
            ],
        )
        obj2 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            links=[ObjectLink(platform=p2, external_id="bar-merge")],
            values=[
                Value(
                    type=ValueType.TITLE,
                    text="Foo",
                    sources=[ValueSource(platform=p2, score_factor=1)],
                )
            ],
        )
        session.add_all([obj1, obj2])
        session.commit()

        f.process_row(
            external_object_ids=[obj1.id],
            attributes=[],
            links=[(p2, ["bar-merge"])],
            session=session,
        )
        session.commit()
        obj = session.query(ExternalObject).first()

        assert len(obj.values) == 1
        assert len(obj.values[0].sources) == 2
        session.delete(obj)
        session.commit()

        # Let's insert brand new objects
        with raises(AssertionError):
            f.process_row(
                external_object_ids=[], attributes=[(ValueType.TITLE, ["Foo."])]
            )

        f.platform = p1
        f.imported_external_object_type = ExternalObjectType.MOVIE
        f.process_row(
            external_object_ids=[],
            attributes=[(ValueType.TITLE, ["Foo."])],
            links=[(p1, ["foo-bar"])],
            session=session,
        )
        session.commit()

        obj = session.query(ExternalObject).first()
        assert obj
        assert len(obj.links) == 1
        assert obj.links[0].platform == p1
        assert obj.links[0].external_id == "foo-bar"
        assert len(obj.values) == 1
        assert obj.values[0].type == ValueType.TITLE
        assert obj.values[0].text == "Foo."
        assert len(obj.values[0].sources) == 1
        assert obj.values[0].sources[0].platform == p1
        session.delete(obj)
        session.commit()

        # Objects with the same external_id should merge
        obj1 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            links=[ObjectLink(platform=p2, external_id="test-same")],
            values=[
                Value(
                    type=ValueType.TITLE,
                    text="Foo",
                    sources=[ValueSource(platform=p1, score_factor=1)],
                )
            ],
        )
        obj2 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            links=[ObjectLink(platform=p2, external_id="test-same")],
            values=[
                Value(
                    type=ValueType.TITLE,
                    text="Foo",
                    sources=[ValueSource(platform=p2, score_factor=1)],
                )
            ],
        )
        session.add_all([obj1, obj2])
        session.commit()

        f.process_row(
            external_object_ids=[],
            attributes=[],
            links=[(p2, ["test-same"])],
            session=session,
        )
        session.commit()
        obj = session.query(ExternalObject).first()
        assert session.query(ExternalObject).count() == 1

        assert len(obj.values) == 1
        assert len(obj.values[0].sources) == 2
        assert len(obj.links) == 1
        session.delete(obj)
        session.commit()
