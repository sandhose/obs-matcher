import re
from functools import partial

from ..countries import lookup
from .utils import CustomEnum, Transition


class PlatformType(CustomEnum):
    INFO = 1  # Platforms like IMDb
    GLOBAL = 2  # Platforms for global IDs
    TVOD = 3  # Renting VOD
    SVOD = 4  # Subscription based VOD


class ScrapStatus(CustomEnum):
    """Enum representing the current status of a given scrap"""

    SCHEDULED = 1
    """The job isn't started, and waiting to be picked up"""

    RUNNING = 2
    """The job has been picked up by a worker"""

    ABORTED = 3
    """The job was aborted while running or pending"""

    SUCCESS = 4
    """The job has succedded"""

    FAILED = 5
    """The job has failed"""

    __transitions__ = [
        Transition('reschedule', [ABORTED, FAILED], SCHEDULED),
        Transition('run', [SCHEDULED], RUNNING),
        Transition('succeeded', [RUNNING], SUCCESS),
        Transition('failed', [RUNNING], FAILED),
        Transition('abort', [RUNNING], ABORTED),
    ]


class ExportFileStatus(CustomEnum):
    """Current status of an export task"""

    SCHEDULED = 1
    """The job is scheduled to be processed as soon as possible"""

    QUERYING = 2
    """The job was started and is now querying the data"""

    PROCESSING = 3
    """The file being processed"""

    DONE = 4
    """The file is done and ready to download"""

    FAILED = 5
    """The job failed"""

    ABSENT = 6
    """The file was empty or was deleted"""

    __transitions__ = [
        Transition('schedule', [SCHEDULED, FAILED, ABSENT, None], SCHEDULED, doc="Process this file"),
        Transition('start', [SCHEDULED, FAILED, ABSENT], QUERYING),
        Transition('processing', [QUERYING], PROCESSING),
        Transition('done', [PROCESSING, QUERYING], DONE),
        Transition('failed', [SCHEDULED, QUERYING, PROCESSING, FAILED, DONE], FAILED),
        Transition('delete', [DONE, PROCESSING], ABSENT, doc="Delete this file"),
    ]


class ExportFactoryIterator(CustomEnum):
    PLATFORMS = 1
    GROUPS = 2
    COUNTRIES = 3


class ExportRowType(CustomEnum):
    EXTERNAL_OBJECT = 1
    OBJECT_LINK = 2


class ImportFileStatus(CustomEnum):
    UPLOADED = 1
    PROCESSING = 2
    DONE = 3
    FAILED = 4

    __transitions__ = [
        Transition('upload', [UPLOADED, FAILED, None], UPLOADED),
        Transition('process', [UPLOADED], PROCESSING, doc="Process this file"),
        Transition('done', [PROCESSING], DONE),
        Transition('failed', [UPLOADED, PROCESSING, None], FAILED)
    ]


class ExternalObjectType(CustomEnum):
    """A type of object in database."""

    PERSON = 1
    """Represents a person. Can be an actor, director, or anything else"""

    MOVIE = 2
    """Represents a single movie"""

    EPISODE = 3
    """Represents an episode of a series' season"""

    SERIES = 4
    """Represents a (TV) series"""


class Gender(CustomEnum):
    """ISO/IEC 5218 compliant gender enum."""

    NOT_KNOWN = 0
    MALE = 1
    FEMALE = 2
    NOT_APPLICABLE = 9


class RoleType(CustomEnum):
    """A type of role of a person on another object."""

    DIRECTOR = 0
    ACTOR = 1
    WRITER = 2


class ValueType(CustomEnum):
    TITLE = 1
    DATE = 2
    GENRES = 3
    DURATION = 4
    NAME = 5
    COUNTRY = 6

    def fmt(self, value):
        def m(r, t):
            result = re.match(r, t)
            return result.group(1) if result is not None else None

        duration_regex = r'^[^\d]*(\d+(?:.\d*)?)[^\d]*$'
        date_regex = r'(\d{4})'
        parenthesis_regex = r'\([^)]*\)'
        fmt_map = {
            ValueType.DURATION: partial(m, duration_regex),
            ValueType.COUNTRY: lookup,
            ValueType.DATE: partial(m, date_regex),
            ValueType.TITLE: lambda t: re.sub(parenthesis_regex, '', t).strip()
        }

        return fmt_map.get(self, lambda _: None)(value)
