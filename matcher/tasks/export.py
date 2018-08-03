from matcher import celery
from matcher.app import db
from matcher.scheme.enums import ExportFileStatus
from matcher.scheme.export import ExportFactory, ExportFile
from matcher.scheme.platform import Session


@celery.task(autoretry_for=(Exception, ), max_retries=5, acks_late=True)
def run_factory(factory_id, session_id):
    scrap_session = db.session.query(Session).get(session_id)
    factory = db.session.query(ExportFactory).get(factory_id)

    assert scrap_session
    assert factory

    for file in factory.generate(scrap_session=scrap_session):
        file.status = ExportFileStatus.SCHEDULED
        if file.count_links(session=db.session) > 0:
            file.schedule(celery=celery)
            db.session.add(file)

    db.session.commit()


@celery.task(autoretry_for=(Exception, ), max_retries=5, acks_late=True)
def process_file(file_id):
    file = db.session.query(ExportFile).get(file_id)
    assert file

    try:
        file.start()
    except Exception as e:  # FIXME: be more specific?
        file.failed(message=str(e))
        db.session.add(file)
        db.session.commit()
        raise e

    file.done()
    db.session.add(file)
    db.session.commit()
