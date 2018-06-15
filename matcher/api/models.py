from flask_restplus import Mask, Model, fields

platform_base = Model('Platform base', {
    'id': fields.Integer,
    'type': fields.String(enum=['tvod', 'svod', 'global', 'info']),
    'slug': fields.String,
    'name': fields.String,
    'country': fields.String,
    'base_score': fields.Integer,
    'group_id': fields.Integer,
})

platform_group = Model('Platform Group', {
    'id': fields.Integer,
    'name': fields.String,
    'platforms': fields.List(fields.Nested(platform_base))
}, mask='id,name,platforms{id,type,slug,name,country}')

platform = platform_base.clone('Platform', {
    'group': fields.Nested(platform_group, allow_null=True),
})

# It works, alright?
platform.__mask__ = Mask('id,type,slug,name,country,group{id,name}')
