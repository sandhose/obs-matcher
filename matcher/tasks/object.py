from matcher import celery
from matcher.app import db
from matcher.scheme.object import ExternalObject
from matcher.scheme.platform import Scrap


@celery.task
def insert_dict(data, scrap_id):
    scrap = db.session.query(Scrap).get(scrap_id)
    assert scrap

    data = ExternalObject.normalize_dict(data)

    # FIXME: kinda ugly workaround
    assert data['type'] is not None  # and request.json.data['type'] != 'any':
    assert data['relation'] is None
    ExternalObject.insert_dict(data, scrap)
