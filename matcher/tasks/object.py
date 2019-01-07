from sqlalchemy.exc import ResourceClosedError

from matcher import celery
from matcher.app import db
from matcher.scheme.object import ExternalObject
from matcher.scheme.platform import Scrap
from matcher.scheme.views import (AttributesView,
                                  PlatformSourceOrderByValueType,
                                  ValueScoreView,)


@celery.task(autoretry_for=(ResourceClosedError, ), max_retries=5)
def insert_dict(data, scrap_id):
    scrap = db.session.query(Scrap).get(scrap_id)
    assert scrap

    data = ExternalObject.normalize_dict(data)

    # FIXME: kinda ugly workaround
    assert data['type'] is not None or data['any_type']
    assert data['relation'] is None
    ExternalObject.insert_dict(data, scrap)


@celery.task
def refresh_attributes():
    ValueScoreView.refresh(session=db.session, concurrently=True)
    PlatformSourceOrderByValueType.refresh(session=db.session, concurrently=True)
    AttributesView.refresh(session=db.session, concurrently=True)
    db.session.commit()
