from flask_restplus import Mask, Model, fields
from matcher.scheme.enums import PlatformType
from matcher.scheme.platform import ScrapStatus

platform_base = Model(
    "Platform base",
    {
        "id": fields.Integer,
        "type": fields.String(enum=[str(t) for t in PlatformType]),
        "slug": fields.String,
        "name": fields.String,
        "country": fields.String,
        "base_score": fields.Integer,
        "group_id": fields.Integer,
    },
)

platform_group = Model(
    "Platform Group",
    {
        "id": fields.Integer,
        "name": fields.String,
        "platforms": fields.List(fields.Nested(platform_base)),
    },
    mask="id,name,platforms{id,type,slug,name,country}",
)

platform = platform_base.clone(
    "Platform", {"group": fields.Nested(platform_group, allow_null=True)}
)

# It works, alright?
platform.__mask__ = Mask("id,type,slug,name,country,group{id,name}")


scrap = Model(
    "Scrap",
    {
        "id": fields.Integer,
        "date": fields.DateTime,
        "status": fields.String(choice=[str(s) for s in ScrapStatus]),
        "platform": fields.Nested(platform),
        "stats": fields.Raw(),
    },
    mask="id,date,status,platform{id,name,slug}",
)


queue = Model(
    "Queue", {"workers": fields.List(fields.String(example="celery@c679340222ca"))}
)
