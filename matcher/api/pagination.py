import math
from functools import wraps
from flask_restplus import reqparse, fields, Model

arguments = reqparse.RequestParser()
arguments.add_argument('page', type=int, required=False, default=1)
arguments.add_argument('per_page', type=int, required=False,
                       choices=[5, 10, 20, 30, 40, 50], default=10)


model = Model('Pagination', {
    'page': fields.Integer(description='Number of this page of results'),
    'pages': fields.Integer(description='Total number of pages of results'),
    'per_page': fields.Integer(description='Number of items per page of results'),
    'total': fields.Integer(description='Total number of results'),
})


def wrap_query(query):
    args = arguments.parse_args()
    start = (args['page'] - 1) * args['per_page']
    end = start + args['per_page']
    total = query.count()
    return query[start:end], {
        'page': args['page'],
        'per_page': args['per_page'],
        'total': total,
        'pages': int(math.ceil(float(total) / args['per_page']))
    }


def wrap(api, _model):
    def decorator(func):
        api.add_model('Pagination', model)
        wrapped_model = api.model('{name} page'.format(name=_model.name), {
            'items': fields.List(fields.Nested(_model)),
            'pagination': fields.Nested(model)
        })

        @api.marshal_with(wrapped_model)
        @api.expect(arguments)
        @wraps(func)
        def f(*args, **kwargs):
            query = func(*args, **kwargs)
            query, pagination = wrap_query(query)
            return {
                'items': query,
                'pagination': pagination,
            }
        return f
    return decorator
