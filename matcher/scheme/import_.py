import codecs
import csv
import logging
from collections import namedtuple
from contextlib import contextmanager
from io import TextIOWrapper
from typing import Dict, List, Tuple, Union

import ftfy.bad_codecs  # noqa
from chardet.universaldetector import UniversalDetector
from sqlalchemy import (TIMESTAMP, Column, Enum, ForeignKey, Integer, Sequence,
                        String, Table, column, func, orm, select, table,
                        tuple_,)
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy.orm import column_property, relationship

from matcher.exceptions import LinksOverlap, ObjectTypeMismatchError
from matcher.utils import import_path

from .base import Base
from .enums import ExternalObjectType, ImportFileStatus, ValueType
from .object import ExternalObject, ObjectLink
from .platform import Platform
from .utils import after, before, inject_session
from .value import Value, ValueSource

logger = logging.getLogger(__name__)

__all__ = ['ImportFile', 'ImportFileLog']

attr_type = namedtuple('attribute', 'type text score_factor')


import_link = Table(
    'import_link',
    Base.metadata,
    Column('import_file_id',
           ForeignKey('import_file.id', ondelete='CASCADE', onupdate='CASCADE'),
           primary_key=True),
    Column('object_link_id',
           ForeignKey('object_link.id',
                      ondelete='CASCADE',
                      onupdate='CASCADE'),
           primary_key=True),
)


@ImportFileStatus.act_as_statemachine('status')
class ImportFile(Base):
    __tablename__ = 'import_file'

    import_file_id_seq = Sequence('import_file_id_seq', metadata=Base.metadata)
    id = Column(Integer, import_file_id_seq, server_default=import_file_id_seq.next_value(), primary_key=True)

    status = Column(Enum(ImportFileStatus), default=None, nullable=False)
    filename = Column(String, nullable=False)
    fields = Column(HSTORE, nullable=False)

    platform_id = Column(Integer, ForeignKey(Platform.id), nullable=True)
    """The platform the new object and attributes will be assigned to"""

    imported_external_object_type = Column(Enum(ExternalObjectType), nullable=True)
    """The type of the newly imported objects"""

    platform = relationship(Platform, back_populates='imports')
    logs = relationship('ImportFileLog', back_populates='file')

    last_activity = column_property(
        select([column('timestamp')]).
        select_from(table('import_file_log')).
        where(column('import_file_id') == id).
        order_by(column('timestamp').desc()).
        limit(1),
        deferred=True
    )

    links = relationship('ObjectLink',
                         secondary='import_link',
                         back_populates='imports')

    sessions = relationship('Session',
                            secondary='session_import_file',
                            back_populates='imports')

    def __init__(self, **kwargs):
        super(ImportFile, self).__init__(**kwargs)
        self._codec = None

    @orm.reconstructor
    def init_on_load(self):
        self._codec = None
        self._line_count = None

    @before('upload')
    def upload_file(self, file):
        self.filename = file.filename
        self.fields = {}

    @property
    def path(self):
        return import_path() / (str(self.id) + '.csv')

    def open(self):
        file = self.path.open(mode='rb')

        if not self._codec:
            detector = UniversalDetector()
            for line in file.readlines():
                detector.feed(line)
                if detector.done:
                    break
            detector.close()
            file.seek(0)
            codec = detector.result['encoding']

            try:
                self._codec = codecs.lookup('sloppy-' + codec)
            except LookupError:
                self._codec = codecs.lookup(codec)

        return TextIOWrapper(file, encoding=self._codec.name)

    def get_line_count(self):
        if self._line_count is None:
            try:
                with self.open() as f:
                    self._line_count = sum(1 for line in f)
            except Exception:
                self._line_count = 0

        return self._line_count

    def get_codec(self):
        if not self._codec:
            self.open().close()

        return self._codec.name

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
            if not value:
                continue

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

            # Start reading the file
            for ln, line in enumerate(reader):
                logger.info("Processing line %d", ln)
                ids, attributes, links = self.map_line(fields, line)
                # Map the platforms slugs to real platform objects
                links = [(platforms[key], ids) for key, ids in links]

                self.process_row(ids, attributes, links, session=session)

    @inject_session
    def reduce_or_create_ids(self, external_object_ids: List[int], session=None):
        """Reduce a list of ExternalObject.id into a single (merged) ExternalObject. Creates a new one when empty"""
        if external_object_ids:
            # If there are external_object_ids, fetch the first and merge the rest
            ids = iter(set(external_object_ids))
            obj = session.query(ExternalObject).get(next(ids))

            # Merge the additional external_object_ids
            for id_ in ids:
                to_merge = session.query(ExternalObject).get(id_)
                if to_merge:
                    if obj is None:
                        obj = to_merge
                    else:
                        try:
                            to_merge.merge_and_delete(obj, session=session)
                        except (LinksOverlap, ObjectTypeMismatchError):
                            logger.warn('Error while merging', exc_info=True)
        else:
            # else create a new object
            assert self.imported_external_object_type
            obj = ExternalObject(type=self.imported_external_object_type)
            session.add(obj)

        session.commit()
        return obj

    @inject_session
    def find_additional_links(self, links: List[Tuple[Platform, List[str]]], session=None):
        """Find additional ExternalObjects from the links"""
        tuples = [(p.id, external_id) for (p, external_ids) in links for external_id in external_ids]
        ids = session.query(ObjectLink.external_object_id).\
            filter(tuple_(ObjectLink.platform_id, ObjectLink.external_id).in_(tuples)).\
            all()
        return [id_ for (id_, ) in ids]

    @inject_session
    def process_row(self,
                    external_object_ids: List[int],
                    attributes: List[Tuple[ValueType, List[str]]],
                    links: List[Tuple[Platform, List[str]]],
                    session=None) -> None:
        # This does a lot of things.
        # We have three type of data possible in a row:
        #  - `ExternalObject.id`s, that should be merged in one object
        #  - A list of links for this row
        #  - A list of attributes to add
        #
        # First thing we do is to list all the objects that should be merged.
        # This includes the provided external_object_ids and the one we can
        # find using the provided links.
        #
        # If no ExternalObject was found, we create a new one, using the
        # `imported_external_object_type` provided in the ImportFile
        #
        # After everything is merged, we need to check what ObjectLink needs to
        # be replaced. Those are first deleted, and all the values that were
        # added by the associated platforms are deleted as well.
        #
        # The last step is to add the attributes that were provided. For this
        # we need to have a platform set in the ImportFile, because the value
        # need to have a source in order to have a score big enough.
        #
        # One caveat: it **is possible** to insert new objects without link to
        # the platform, which can lead to duplicates and orphan objects.
        #
        # The whole thing is not transactionnal and might f*ck everything up.
        # This needs to be tested a lot before using it for real.

        if attributes:
            # If we want to insert attributes we need a platform to which to assign them
            assert self.platform

        if len(external_object_ids) > 0:
            # We are about to add new links, remove the old one and clear the attributes set by it
            for (platform, external_ids) in links:
                if len(external_ids) == 0:
                    continue

                logger.info('Deleting links (%r, %r)', platform, external_ids);
                existing_links = session.query(ObjectLink).\
                    filter(ObjectLink.platform == platform,
                           ObjectLink.external_object_id.in_(external_object_ids),
                           ~ObjectLink.external_id.in_(external_ids)).\
                    delete(synchronize_session=False)

                if existing_links:
                    logger.info('A link was removed, deleting values')
                    # Delete the values that were associated with this platform
                    session.query(ValueSource).\
                        filter(ValueSource.platform == platform).\
                        filter(ValueSource.value_id.in_(
                            session.query(Value.id).filter(Value.external_object_id.in_(external_object_ids))
                        )).\
                        delete(synchronize_session=False)

            session.commit()

        # Fetch other existing external_object_ids from the links
        external_object_ids += self.find_additional_links(links=links, session=session)

        if len(external_object_ids) <= 1 and not attributes and not links:
            return

        # Get one merged ExternalObject
        obj = self.reduce_or_create_ids(external_object_ids, session=session)

        if obj is None:
            logger.error('External object not found %r', external_object_ids)
            return

        # Add the new links
        for (platform, external_ids) in links:
            for external_id in external_ids:
                link = session.query(ObjectLink).\
                    filter(ObjectLink.external_id == external_id,
                           ObjectLink.platform == platform,
                           ObjectLink.external_object == obj).\
                    first()

                if not link:
                    link = ObjectLink(external_object=obj,
                                      platform=platform,
                                      external_id=external_id)

                if platform == self.platform:
                    self.links.append(link)

        session.commit()

        attributes_list = set()

        # Map the attributes to dicts accepted by add_attribute
        for (type_, values) in attributes:
            # The values are weighed by their position in the array
            for scale, value in enumerate(reversed(values), 1):
                attributes_list.add(attr_type(type_, value, 1 * scale))

                # Format the attribute (e.g. map to ISO code or extract the year in a date)
                fmt = type_.fmt(value)
                if fmt and fmt != value:
                    attributes_list.add(attr_type(type_, fmt, 1.2 * scale))

        for attribute in attributes_list:
            obj.add_attribute(dict(attribute._asdict()), self.platform)

        # Cleanup attributes with no sources
        session.query(Value).\
            filter(Value.external_object_id == obj.id).\
            filter(~Value.sources.any()).\
            delete(synchronize_session=False)
        session.commit()

        logger.info('Imported  %r', obj)

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
