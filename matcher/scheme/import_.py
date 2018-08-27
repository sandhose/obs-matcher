import csv
from contextlib import contextmanager
from io import TextIOWrapper
from typing import Dict, List, Tuple, Union

from chardet.universaldetector import UniversalDetector
from sqlalchemy import (TIMESTAMP, Column, Enum, ForeignKey, Integer, Sequence,
                        String, column, func, select, table,)
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy.orm import column_property, relationship

from matcher.utils import import_path

from .base import Base
from .enums import ImportFileStatus, ValueType
from .platform import Platform
from .utils import after, before, inject_session

__all__ = ['ImportFile', 'ImportFileLog']


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
        return import_path() / (str(self.id) + '.csv')

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

    def map_fields(self, header: list) -> Dict[str, Union[List[int], Dict[str, List[int]]]]:
        """Map self.fields to header indexes"""
        output = {
            'external_object_id': [],
            'attribute': {},
            'attribute_list': {},
            'link': {}
        }  # type: Dict[str, Union[List[int], Dict[str, List[int]]]]

        for key, value in self.fields.items():
            indexes = [idx for idx, column in enumerate(header) if column == key]
            type_, _, arg = value.partition('.')
            assert type_, key + " is empty"
            assert indexes, "no matching columns found for " + key

            out = output[type_]

            if isinstance(out, list):
                assert not arg, type_ + " should have no argument"
                out.extend(indexes)
            elif isinstance(out, dict):
                assert arg, type_ + " needs an argument"
                out[arg] = out.get(arg, []) + indexes

        return output

    def map_line(self, fields, line: List[str]) -> \
            Tuple[List[int], List[Tuple[ValueType, List[str]]], List[Tuple[Platform, List[str]]]]:
        external_object_ids = [int(line[i]) for i in fields['external_object_id'] if line[i]]

        attributes = []  # type: List[Tuple[ValueType, List[str]]]
        for attribute in ValueType:
            attr_list = []  # type: List[str]
            attr_list += [line[i] for i in fields['attribute'].get(str(attribute), []) if line[i]]
            attr_list += [l for i in fields['attribute_list'].get(str(attribute), [])
                          for l in line[i].split(',') if l]
            if attr_list:
                attributes.append((attribute, attr_list))

        links = []  # type: List[Tuple[Platform, List[str]]]
        for key, value in fields['link'].items():
            key = key.replace('_', '-')  # FIXME: not sure if this is a good idea
            link_list = [line[i] for i in value if line[i]]
            if link_list:
                links.append((key, link_list))

        return external_object_ids, attributes, links

    @after('process')
    @inject_session
    def process_import(self, session=None):
        with self.csv_reader() as reader:
            # Fetch the header and map to fields
            header = next(reader)
            fields = self.map_fields(header)

            # Cache needed platforms
            platforms = {}
            for key in fields['link']:
                platforms[key] = Platform.lookup(session, key.replace('_', '-'))
                assert platforms[key]

            # For now we don't support insertion of new objects
            assert fields['external_object_id'], "no external_object_id"

            # Start reading the file
            for line in reader:
                ids, attributes, links = self.map_line(fields, line)
                # Map the platforms slugs to real platform objects
                links = [(platforms[key], ids) for key, ids in links]

                print(ids, attributes, links)

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
