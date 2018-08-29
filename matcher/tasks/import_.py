from matcher import celery
from matcher.app import db
from matcher.scheme.import_ import ImportFile


@celery.task(autoretry_for=(Exception, ), max_retries=5)
def process_file(file_id):
    file = db.session.query(ImportFile).get(file_id)
    assert file

    try:
        file.process()
    except Exception as e:  # FIXME: be more specific?
        file.failed(message=str(e))
        db.session.add(file)
        db.session.commit()
        raise e

    file.done()
    db.session.add(file)
    db.session.commit()