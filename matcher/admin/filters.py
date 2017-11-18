from flask_admin.model.filters import BaseFilter
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.types import Integer, Float
from sqlalchemy.sql import column
import json


class ExternalObjectPlatformFilter(BaseFilter):
    def __init__(self, column, name, options=None, data_type=None):
        super(ExternalObjectPlatformFilter, self).__init__(name, options,
                                                           data_type)
        self.column = column

    def apply(self, query, value, alias=None):
        from ..scheme.object import ObjectLink, ExternalObject
        from ..scheme.platform import Platform

        return query.\
            join(ObjectLink,
                 ExternalObject.id == ObjectLink.external_object_id).\
            join(Platform, ObjectLink.platform_id == Platform.id).\
            filter(self.column == value)

    def operation(self):
        return 'is'


class ExternalObjectSimilarFilter(BaseFilter):
    def apply(self, query, value, alias=None):
        from ..scheme.object import ExternalObject

        similar = list(ExternalObject.query.get(int(value)).similar())
        json_data = json.dumps([s._asdict() for s in similar])

        c = column('data', JSON)
        subquery = select([
            c['into'].astext.cast(Integer).label('into'),
            c['score'].astext.cast(Float).label('score')
        ])\
            .select_from(func.json_array_elements(json_data).alias('data'))\
            .alias('similar')

        query = query.join(subquery,
                           subquery.c.into == ExternalObject.id)

        if getattr(query, 'order_similar', False):
            print('order_similar')
            query = query.order_by(subquery.c.score)

        return query

    def operation(self):
        return 'similar to'
