from flask_admin import Admin

from ..app import db
from ..scheme.object import ObjectLink
from ..scheme.platform import Platform, PlatformGroup, Scrap
from ..scheme.value import Value, ValueSource
from .views import (AllObjectView, MovieObjectView, ObjectLinkView,
                    PersonObjectView, PlatformGroupView, PlatformView,
                    ScrapView, ValueSourceView, ValueView)


def setup_admin(app):
    admin = Admin(base_template='admin_master.html')
    admin.add_views(
        PlatformView(Platform, db.session, name='Platform',
                     category='Platforms'),
        PlatformGroupView(PlatformGroup, db.session,
                          name='Group', category='Platforms'),
        ScrapView(Scrap, db.session, name='Scrap', category='Platforms'),
        ValueView(Value, db.session, name='Value', category='Values'),
        ValueSourceView(ValueSource, db.session, name='Source',
                        category='Values'),
        ObjectLinkView(ObjectLink, db.session),
        AllObjectView(db.session, name='All'),
        PersonObjectView(db.session, name='Persons'),
        MovieObjectView(db.session, name='Movies'),
    )
    admin.init_app(app, endpoint='admin', url='/admin')
