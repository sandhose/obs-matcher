from matcher import db
from .mixins import ResourceMixin, CustomEnum
from .object import ExternalObjectType


class JobStatus(CustomEnum):
    PENDING = 1
    SCHEDULED = 2
    ABORTED = 3
    SUCCESS = 4
    FAILED = 5


class Job(db.Model, ResourceMixin):
    __tablename__ = 'queue_job'

    id = db.Column(db.Integer,
                   db.Sequence('queue_job_id_seq'),
                   primary_key=True)

    platform_id = db.Column(db.Integer,
                            db.ForeignKey('platform.id'),
                            nullable=False)

    scrap_id = db.Column(db.Integer,
                         db.ForeignKey('scrap.id'))

    platform = db.relationship('Platform')
    scrap = db.relationship('Scrap')
    type = db.Column(db.Enum(ExternalObjectType), nullable=False)
    data = db.Column(db.JSON)
    status = db.Column(db.Enum(JobStatus),
                       nullable=False,
                       default=JobStatus.PENDING)
