from flask_admin import Admin

from ..app import db
from .views import DefaultView, ExternalObjectView, PlatformGroupView, \
    PlatformView, ValueView, ObjectLinkView, ScrapView
from ..scheme.platform import Platform, PlatformGroup, Scrap
from ..scheme.value import Value, ValueSource
from ..scheme.object import ObjectLink, ObjectLinkWorkMeta, ExternalObject, \
    Person, Episode, Season


def setup_admin(app):
    admin = Admin(base_template='admin_master.html')
    admin.add_views(
        PlatformView(Platform, db.session, name='Platform',
                     category='Platforms'),
        PlatformGroupView(PlatformGroup, db.session,
                          name='Group', category='Platforms'),
        ScrapView(Scrap, db.session, name='Scrap', category='Platforms'),
        ValueView(Value, db.session, name='Value', category='Values'),
        DefaultView(ValueSource, db.session, name='Source', category='Values'),
        ObjectLinkView(ObjectLink, db.session),
        DefaultView(ObjectLinkWorkMeta, db.session),
        ExternalObjectView(ExternalObject, db.session),
        DefaultView(Person, db.session),
        DefaultView(Episode, db.session, name='Episode', category='Works'),
        DefaultView(Season, db.session, name='Season', category='Works'),
    )
    admin.init_app(app, endpoint='admin', url='/admin')
