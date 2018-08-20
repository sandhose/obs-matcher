from contextlib import contextmanager
from io import TextIOWrapper
import csv
import codecs
from pathlib import Path

from chardet.universaldetector import UniversalDetector
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

    def open(self):
        file = self.path.open(mode='rb')

        detector = UniversalDetector()
        for line in file.readlines():
            detector.feed(line)
            if detector.done:
                break
        detector.close()
        file.seek(0)
        codec = detector.result['encoding']

        return TextIOWrapper(file, encoding=codec)

    def detect_dialect(self, f):
        extract = ''.join(line for line in f.readlines()[:100])
        return csv.Sniffer().sniff(extract)

    @contextmanager
    def csv_reader(self):
        with self.open() as f:
            dialect = self.detect_dialect(f)
            f.seek(0)
            yield csv.reader(f, dialect=dialect)

    def header(self):
        try:
            with self.csv_reader() as r:
                return next(r)
        except (IOError, UnicodeError):
            # FIXME: handle those errors
            return []

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
