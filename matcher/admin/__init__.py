from flask_admin import Admin

from ..app import db
from .views import DefaultView, ExternalObjectView, PlatformGroupView, \
    PlatformView, ValueView
from ..scheme.platform import Platform, PlatformGroup, Scrap
from ..scheme.value import Value, ValueSource
from ..scheme.object import ObjectLink, ObjectLinkWorkMeta, ExternalObject, \
    Person, Episode, Season


admin = Admin()
admin.add_views(
    PlatformView(Platform, db.session, name='Platform', category='Platforms'),
    PlatformGroupView(PlatformGroup, db.session,
                      name='Group', category='Platforms'),
    DefaultView(Scrap, db.session, name='Scrap', category='Platforms'),
    ValueView(Value, db.session, name='Value', category='Values'),
    DefaultView(ValueSource, db.session, name='Source', category='Values'),
    DefaultView(ObjectLink, db.session),
    DefaultView(ObjectLinkWorkMeta, db.session),
    ExternalObjectView(ExternalObject, db.session),
    DefaultView(Person, db.session),
    DefaultView(Episode, db.session, name='Episode', category='Works'),
    DefaultView(Season, db.session, name='Season', category='Works'),
)
