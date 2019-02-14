from functools import wraps

from flask_restplus import Model, fields, reqparse

pagination_arguments = reqparse.RequestParser()
pagination_arguments.add_argument("page", type=int, required=False, default=1)
pagination_arguments.add_argument(
    "per_page", type=int, required=False, choices=[5, 10, 20, 30, 40, 50], default=10
)


model = Model(
    "Pagination",
    {
        "page": fields.Integer(description="Number of this page of results"),
        "pages": fields.Integer(description="Total number of pages of results"),
        "per_page": fields.Integer(description="Number of items per page of results"),
        "total": fields.Integer(description="Total number of results"),
        "has_next": fields.Boolean(description="Does it have a next page?"),
        "has_prev": fields.Boolean(description="Does it have a previous page?"),
    },
)


def wrap(api, _model, arguments=[]):
    def decorator(func):
        api.add_model("Pagination", model)
        wrapped_model = api.model(
            "{name} page".format(name=_model.name),
            {
                "items": fields.List(fields.Nested(_model)),
                "pagination": fields.Nested(model),
            },
        )

        @api.marshal_with(wrapped_model)
        @api.expect(pagination_arguments, *arguments)
        @wraps(func)
        def f(*args, **kwargs):
            pagination = func(*args, **kwargs).paginate()
            return {"items": pagination.items, "pagination": pagination}

        return f

    return decorator
