from matcher.scheme.enums import ExternalObjectType, ValueType
from matcher.scheme.object import ExternalObject
from matcher.scheme.platform import Platform
from matcher.scheme.value import Value, ValueSource


class TestExternalObjectMerge(object):
    def test_source_merging(self, session):
        platform1 = Platform(name='Platform 1', slug='platform-1',
                             base_score=200)
        platform2 = Platform(name='Platform 2', slug='platform-2',
                             base_score=300)
        session.add_all([platform1, platform2])

        object1 = ExternalObject(type=ExternalObjectType.MOVIE)
        object2 = ExternalObject(type=ExternalObjectType.MOVIE)
        session.add_all([object1, object2])

        value1 = Value(external_object=object1,
                       type=ValueType.TITLE,
                       text="Foo",
                       sources=[ValueSource(platform=platform1,
                                            score_factor=200)])
        value2 = Value(external_object=object2,
                       type=ValueType.TITLE,
                       text="Foo",
                       sources=[ValueSource(platform=platform2,
                                            score_factor=300)])
        session.add_all([value1, value2])

        session.commit()

        object2.merge_and_delete(object1, session)
        session.expire_all()

        assert len(object1.values) == 1
        assert value1.external_object == object1
        assert value1.score == (200 * 200 + 300 * 300)
        assert len(value1.sources) == 2

        assert session.query(ExternalObject).count() == 1

    def test_value_moving(self, session):
        # This tests for moving a lot of values at once. There was an issue of
        # value disappearing, hence this test.
        platform1 = Platform(name='Platform 1', slug='platform-1',
                             base_score=200)
        platform2 = Platform(name='Platform 2', slug='platform-2',
                             base_score=300)
        session.add_all([platform1, platform2])

        object1 = ExternalObject(type=ExternalObjectType.MOVIE)
        object2 = ExternalObject(type=ExternalObjectType.MOVIE)
        session.add_all([object1, object2])

        # The first 5 values are on both platforms, while the 5 others are only
        # on the second one. With this, the first 5 should only have their
        # sources moved, while the 5 others should have the whole value moved
        values1 = [
            Value(external_object=object1,
                  type=ValueType.TITLE,
                  text="{}".format(i),
                  sources=[ValueSource(platform=platform1,
                                       score_factor=100 * i)])
            for i in range(5)
        ]
        values2 = [
            Value(external_object=object2,
                  type=ValueType.TITLE,
                  text="{}".format(i),
                  sources=[ValueSource(platform=platform2,
                                       score_factor=100 * i)])
            for i in range(10)
        ]
        session.add_all(values1 + values2)

        session.commit()

        object2.merge_and_delete(object1, session)
        session.expire_all()

        seen_indexes = set()
        for value in object1.values:
            # Retrieve the `i` from the value text
            index = int(value.text)
            seen_indexes.add(index)

            if index < 5:  # those should have two sources
                assert len(value.sources) == 2
                assert value.score == index * 100 * (200 + 300)
                assert value.sources[0].score_factor == index * 100
                assert value.sources[1].score_factor == index * 100
            else:
                assert len(value.sources) == 1
                assert value.score == index * 100 * 300
                assert value.sources[0].platform == platform2
                assert value.sources[0].score_factor == index * 100

        assert len(seen_indexes) == 10  # all indexes should have been unique
        assert len(object1.values) == 10

        assert session.query(ExternalObject).count() == 1
        assert session.query(Value).count() == 10
        assert session.query(ValueSource).count() == 15
