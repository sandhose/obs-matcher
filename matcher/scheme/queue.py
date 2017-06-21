from matcher import db
from .mixins import ResourceMixin
from .object import ExternalObjectType


class Job(db.Model, ResourceMixin):
    __tablename__ = 'queue_job'

    id = db.Column(db.Integer,
                   db.Sequence('queue_job_id_seq'),
                   primary_key=True)

    # platform = …
    # scrap = …
    # type = …
    # data = …
    # status = …
