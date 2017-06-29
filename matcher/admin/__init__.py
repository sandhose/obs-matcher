from flask_admin import Admin

from .. import db
from .views import DefaultView, ExternalObjectView, PlatformGroupView
from ..scheme import Platform, PlatformGroup, Scrap, Value, ValueSource, \
    ObjectLink, ObjectLinkWorkMeta, ExternalObject, Person, Episode, \
    Season, Job


def setup_admin(app):
    admin = Admin(app)

    admin.add_view(DefaultView(Platform, db.session, name='Platform',
                               category='Platforms'))
    admin.add_view(PlatformGroupView(PlatformGroup, db.session, name='Group',
                                     category='Platforms'))
    admin.add_view(DefaultView(Scrap, db.session, name='Scrap',
                               category='Platforms'))
    admin.add_view(DefaultView(Value, db.session, name='Value',
                               category='Values'))
    admin.add_view(DefaultView(ValueSource, db.session, name='Source',
                               category='Values'))
    admin.add_view(DefaultView(ObjectLink, db.session))
    admin.add_view(DefaultView(ObjectLinkWorkMeta, db.session))
    admin.add_view(ExternalObjectView(ExternalObject, db.session))
    admin.add_view(DefaultView(Person, db.session))
    admin.add_view(DefaultView(Episode, db.session, name='Episode',
                               category='Works'))
    admin.add_view(DefaultView(Season, db.session, name='Season',
                               category='Works'))
    admin.add_view(DefaultView(Job, db.session, name='Job'))
