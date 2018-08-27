from pytest import raises

from ..enums import ExternalObjectType, ValueType
from ..import_ import ImportFile
from ..object import ExternalObject, ObjectLink
from ..platform import Platform
from ..value import Value, ValueSource


class TestImportFile(object):
    def test_map_fields(self):
        file = ImportFile(fields={
            'foo': 'external_object_id',
            'bar': 'attribute.title',
            'baz': 'attribute_list.genres'
        })

        assert file.map_fields(['col', 'foo', 'bar', 'baz']) == {
            'external_object_id': [1],
            'attribute': {'title': [2]},
            'attribute_list': {'genres': [3]},
            'link': {},
        }

        # Repeating fields
        file = ImportFile(fields={
            'foo': 'external_object_id',
        })

        assert file.map_fields(['foo', 'foo', 'bar', 'foo']) == {
            'external_object_id': [0, 1, 3],
            'attribute': {},
            'attribute_list': {},
            'link': {},
        }

        # Repeating fields with args
        file = ImportFile(fields={
            'title': 'attribute.title',
            'date': 'attribute.date',
        })

        assert file.map_fields(['title', 'title', 'date', 'date']) == {
            'external_object_id': [],
            'attribute': {'title': [0, 1], 'date': [2, 3]},
            'attribute_list': {},
            'link': {},
        }

        # Raises on invalid fields
        with raises(KeyError):
            ImportFile(fields={'foo': 'foo'}).map_fields(['foo'])

        # Raises when the column was not found
        with raises(AssertionError):
            ImportFile(fields={'foo': 'external_object_id'}).map_fields([])

        # Raises when no arg was given
        with raises(AssertionError):
            ImportFile(fields={'foo': 'attribute'}).map_fields(['foo'])

    def test_process_row(self, session):
        f = ImportFile()
        p1 = Platform(name='Foo', slug='foo')
        p2 = Platform(name='Bar', slug='bar')

        # First (simple) case: merge two IDs
        obj1 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            values=[
                Value(type=ValueType.TITLE, text='Foo',
                      sources=[ValueSource(platform=p1, score_factor=1)])
            ])
        obj2 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            values=[
                Value(type=ValueType.TITLE, text='Bar',
                      sources=[ValueSource(platform=p2, score_factor=1)])
            ])

        session.add_all([p1, p2, obj1, obj2])
        session.commit()

        f.process_row(external_object_ids=[obj1.id, obj2.id], attributes=[], links=[], session=session)
        session.commit()

        assert len(obj1.values) == 2
        session.delete(obj1)
        session.commit()

        # Links should be added
        obj1 = ExternalObject(type=ExternalObjectType.MOVIE)
        session.add(obj1)
        session.commit()

        f.process_row(external_object_ids=[obj1.id], attributes=[], links=[(p1, "foo-0")], session=session)
        session.commit()

        assert len(obj1.links) == 1
        assert obj1.links[0].platform == p1
        assert obj1.links[0].external_id == "foo-0"

        # Testing here that values associated by a replaced link are being evicted
        obj1 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            links=[
                ObjectLink(platform=p1, external_id="foo-1"),
            ],
            values=[Value(type=ValueType.TITLE, text='Foo',
                          sources=[ValueSource(platform=p1, score_factor=1)]),
                    Value(type=ValueType.TITLE, text='Bar',
                          sources=[ValueSource(platform=p2, score_factor=1)])]
        )

        session.add(obj1)
        session.commit()

        f.process_row(external_object_ids=[obj1.id], attributes=[], links=[(p1, "foo-2")], session=session)
        session.commit()

        assert len(obj1.values) == 1
        assert len(obj1.links) == 1
        assert obj1.links[0].external_id == "foo-2"

        session.delete(obj1)
        session.commit()

        # …but should stay if they have another sourcec
        obj1 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            links=[
                ObjectLink(platform=p1, external_id="foo-1"),
            ],
            values=[Value(type=ValueType.TITLE, text='Foo',
                          sources=[ValueSource(platform=p1, score_factor=1),
                                   ValueSource(platform=p2, score_factor=1)])]
        )

        session.add(obj1)
        session.commit()

        f.process_row(external_object_ids=[obj1.id], attributes=[], links=[(p1, "foo-2")], session=session)
        session.commit()

        assert len(obj1.values) == 1
        assert len(obj1.values[0].sources) == 1

        session.delete(obj1)
        session.commit()

        # Objects with the same ID should merge (and their attributes as well)
        obj1 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            values=[Value(type=ValueType.TITLE, text='Foo',
                          sources=[ValueSource(platform=p1, score_factor=1)])]
        )
        obj2 = ExternalObject(
            type=ExternalObjectType.MOVIE,
            links=[ObjectLink(platform=p2, external_id="bar-merge")],
            values=[Value(type=ValueType.TITLE, text='Foo',
                          sources=[ValueSource(platform=p2, score_factor=1)])]
        )
        session.add_all([obj1, obj2])
        session.commit()

        f.process_row(external_object_ids=[obj1.id], attributes=[], links=[(p2, "bar-merge")], session=session)
        session.commit()

        assert len(obj1.values) == 1
        assert len(obj1.values[0].sources) == 2
