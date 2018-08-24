from pytest import raises

from ..import_ import ImportFile


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
        }

        # Repeating fields
        file = ImportFile(fields={
            'foo': 'external_object_id',
        })

        assert file.map_fields(['foo', 'foo', 'bar', 'foo']) == {
            'external_object_id': [0, 1, 3],
            'attribute': {},
            'attribute_list': {},
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
