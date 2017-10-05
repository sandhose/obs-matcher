from restless.constants import UNAVAILABLE, CONFLICT, BAD_REQUEST


class AmbiguousLinkError(Exception):
    """Raise when the lookup ends up returning multiple object"""

    status = UNAVAILABLE

    def resolve(self, session):
        """Resolve the conflict by merging all objects

        :session: The DB session
        """
        obj = self.objects.pop()
        for their in self.objects:
            obj = obj.merge_and_delete(their, session)
        return obj

    def __init__(self, objects):
        self.objects = objects

    def __str__(self):
        return "Existing links resolve to different objects {!r}"\
            .format(self.objects)


class ObjectTypeMismatchError(Exception):
    """Raise when the object found isn't the same type as it should"""

    status = CONFLICT

    def __init__(self, is_type, should_be):
        self.is_type = is_type
        self.should_be = should_be

    def __str__(self):
        return "Object type is {!r}, should be {!r}".format(self.is_type,
                                                            self.should_be)


class UnknownRelation(Exception):
    """The given relation doesn't exists"""

    status = BAD_REQUEST

    def __init__(self, relation):
        self.relation = relation

    def __str__(self):
        return "{!r} is an unknown relation type".format(self.relation)


class InvalidRelation(Exception):
    """The relation can't be set between the two objects"""

    status = BAD_REQUEST

    def __init__(self, relation, parent, child):
        self.relation = relation
        self.parent = parent
        self.child = child

    def __str__(self):
        return "{!r} can't be “{}” {!r}".format(self.parent,
                                                self.relation,
                                                self.child)


class ExternalIDMismatchError(Exception):
    """Raise when two links IDs for the same object/platform mismatch"""

    status = CONFLICT

    def __init__(self, link, external_id):
        self.link = link
        self.external_id = external_id

    def __str__(self):
        return "Link {!r} ID does not match {!r}".format(self.link,
                                                         self.external_id)


class UnknownAttribute(Exception):
    """Raised when an unknown parameter was given"""

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return "Unknown attribute {!r}".format(self.name)


class InvalidStatusTransition(Exception):
    """Raised when the scrap status change fails"""

    def __init__(self, from_status, to_status):
        self.from_status = from_status
        self.to_status = to_status

    def __str__(self):
        return "Invalid transition from {!r} to {!r}".format(self.from_status,
                                                             self.to_status)


class LinkNotFound(Exception):
    """The user tried to insert attributes on an object without adding a link
       to the platform it scaps."""

    status = BAD_REQUEST

    def __init__(self, links, platform):
        self.links = links
        self.platform = platform

    def __str__(self):
        return "Could not find link for {!r} in {!r}".format(self.platform,
                                                             self.links)


class InvalidMetadata(Exception):
    """The given metadata can't be set for this type"""

    status = BAD_REQUEST

    def __init__(self, object_type, key):
        self.object_type = object_type
        self.key = key

    def __str__(self):
        return "Can't add metadata {!r} in type {!r}".format(self.key,
                                                             self.object_type)