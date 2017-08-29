from flask_admin import Admin

from .. import db
from .views import DefaultView, ExternalObjectView, PlatformGroupView, \
    PersonView
from ..scheme.platform import Platform, PlatformGroup, Scrap
from ..scheme.value import Value, ValueSource
from ..scheme.object import ObjectLink, ObjectLinkWorkMeta, ExternalObject, \
    Person, Episode, Season


admin = Admin()
admin.add_views(
    DefaultView(Platform, db.session, name='Platform', category='Platforms'),
    PlatformGroupView(PlatformGroup, db.session,
                      name='Group', category='Platforms'),
    DefaultView(Scrap, db.session, name='Scrap', category='Platforms'),
    DefaultView(Value, db.session, name='Value', category='Values'),
    DefaultView(ValueSource, db.session, name='Source', category='Values'),
    DefaultView(ObjectLink, db.session),
    DefaultView(ObjectLinkWorkMeta, db.session),
    ExternalObjectView(ExternalObject, db.session),
    PersonView(Person, db.session),
    DefaultView(Episode, db.session, name='Episode', category='Works'),
    DefaultView(Season, db.session, name='Season', category='Works'),
)
