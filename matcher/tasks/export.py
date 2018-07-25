from celery import group

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

    # TODO: log when it was scheduled
    files = list(factory.generate(scrap_session=scrap_session))
    db.session.add_all(files)
    db.session.commit()

    group(process_file.s(file.id) for file in files).apply_async()


@celery.task(autoretry_for=(Exception, ), max_retries=5, acks_late=True)
def process_file(file_id):
    file = db.session.query(ExportFile).get(file_id)
    assert file

    try:
        file.process()
    except Exception as e:
        file.change_status(ExportFileStatus.FAILED, message=str(e))
        db.session.add(file)
        db.session.commit()
        raise e

    file.change_status(ExportFileStatus.DONE)
    db.session.add(file)
    db.session.commit()
