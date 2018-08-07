from pathlib import Path
from sqlalchemy import (TIMESTAMP, Column, Enum, ForeignKey, Integer, Sequence,
                        String, column, func, select, table,)
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy.orm import column_property, relationship

from .base import Base
from .enums import ImportFileStatus
from .utils import after, before

__all__ = ['ImportFile']


@ImportFileStatus.act_as_statemachine('status')
class ImportFile(Base):
    __tablename__ = 'import_file'

    import_file_id_seq = Sequence('import_file_id_seq', metadata=Base.metadata)
    id = Column(Integer, import_file_id_seq, server_default=import_file_id_seq.next_value(), primary_key=True)

    status = Column(Enum(ImportFileStatus), default=None, nullable=False)
    filename = Column(String, nullable=False)
    fields = Column(HSTORE, nullable=False)

    logs = relationship('ImportFileLog', back_populates='file')

    last_activity = column_property(
        select([column('timestamp')]).
        select_from(table('import_file_log')).
        where(column('import_file_id') == id).
        order_by(column('timestamp').desc()).
        limit(1),
        deferred=True
    )

    @before('upload')
    def upload_file(self, file):
        self.filename = file.filename
        self.fields = {}

    @property
    def path(self):
        return Path('/tmp/') / (str(self.id) + '.csv')

    @after
    def log_status(self, message=None, *_, **__):
        self.logs.append(ImportFileLog(status=self.status, message=message))


class ImportFileLog(Base):
    __tablename__ = 'import_file_log'

    import_file_log_id_seq = Sequence('import_file_log_id_seq', metadata=Base.metadata)
    id = Column(Integer, import_file_log_id_seq, server_default=import_file_log_id_seq.next_value(), primary_key=True)

    import_file_id = Column(Integer, ForeignKey(ImportFile.id), nullable=False)
    file = relationship('ImportFile', back_populates='logs')

    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    status = Column(Enum(ImportFileStatus), nullable=False)
    message = Column(String)
