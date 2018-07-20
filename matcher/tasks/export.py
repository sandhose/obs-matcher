from celery import group

from matcher import celery
from matcher.app import db
from matcher.scheme.enums import ExportFileStatus
from matcher.scheme.export import ExportFactory, ExportFile
from matcher.scheme.platform import Session


@celery.task
def run_factory(factory_id, session_id):
    scrap_session = db.session.query(Session).get(session_id)
    factory = db.session.query(ExportFactory).get(factory_id)

    assert scrap_session
    assert factory

    files = list(factory.generate(scrap_session=scrap_session))
    db.session.add_all(files)
    db.session.commit()

    group(process_file.s(file.id) for file in files)()


@celery.task(autoretry_for=(Exception, ), max_retries=5)
def process_file(file_id):
    file = db.session.query(ExportFile).get(file_id)
    assert file

    file.process()
    file.status = ExportFileStatus.DONE
    db.session.add(file)
    db.session.commit()
