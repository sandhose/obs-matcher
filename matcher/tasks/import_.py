import logging
from typing import List, Tuple

from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    ResourceClosedError,
    StaleDataError,
)

from matcher import celery
from matcher.app import db
from matcher.scheme.enums import ValueType
from matcher.scheme.import_ import ImportFile
from matcher.scheme.platform import Platform

logger = logging.getLogger(__name__)


@celery.task(base=celery.OnceTask)
def process_file(file_id):
    file = db.session.query(ImportFile).get(file_id)
    assert file

    try:
        file.process()
    except Exception as e:  # FIXME: be more specific?
        # TODO: this should be done inside `process`
        file.failed(message=str(e))
        db.session.add(file)
        db.session.commit()
        raise

    db.session.add(file)
    db.session.commit()


@celery.task()
def mark_done(file_id):
    file = db.session.query(ImportFile).get(file_id)
    assert file

    file.done()
    db.session.add(file)
    db.session.commit()


# Import one row of a file
# TODO: it works but its ugly
@celery.task(
    autoretry_for=(
        ResourceClosedError,
        OperationalError,
        IntegrityError,
        StaleDataError,
    ),
    max_retries=5,
)
def process_row(
    file_id: int,
    external_object_ids: List[int],
    attributes: List[Tuple[str, List[str]]],
    links: List[Tuple[str, List[str]]],
):
    file = db.session.query(ImportFile).get(file_id)
    assert file

    attributes = [(ValueType.from_name(k), v) for (k, v) in attributes]
    links = [
        (Platform.lookup(db.session, key.replace("_", "-")), ids) for key, ids in links
    ]
    logger.debug(
        "Processing row ids=%r attrs=%r links=%r",
        external_object_ids,
        attributes,
        links,
    )
    file.process_row(external_object_ids, attributes, links)
