# -*- coding: utf-8 -*-
"""This modules defines exceptions used in this application.

Notes
-----
Each exception defines a `status` attribute which is used to set the HTTP
status the server should respond with when the exception is raised.

"""


class AmbiguousLinkError(Exception):
    """Raise when the lookup ends up returning multiple object.

    Attributes
    ----------
    objects : array of :obj:`.scheme.object.ExternalObject`
        List of objects that should be merged

    """

    def resolve(self, session):
        """Resolve the conflict by merging all objects.

        :session: The DB session
        """
        obj = self.objects.pop()
        for their in self.objects:
            obj = obj.merge_and_delete(their, session)
        return obj

    def __init__(self, objects):
        """Raise with the objects that should be merged."""
        self.objects = objects

    def __str__(self):
        return "Existing links resolve to different objects {!r}".format(self.objects)


class ObjectTypeMismatchError(Exception):
    """Raise when the object found isn't the same type as it should.

    Attributes
    ----------
    is_type : :obj:`.scheme.object.ExternalObjectType`
        The type the object is currently
    should_be : :obj:`.scheme.object.ExternalObjectType`
        The type the object should be according to its links

    """

    def __init__(self, is_type, should_be):
        """Raise with both types we've got for this object."""
        self.is_type = is_type
        self.should_be = should_be

    def __str__(self):
        return "Object type is {!r}, should be {!r}".format(
            self.is_type, self.should_be
        )


class UnknownRelation(Exception):
    """The given relation doesn't exists.

    Attributes
    ----------
    relation : str
        The relation that was given.

    """

    def __init__(self, relation):
        """Raise for a given unknown relation type."""
        self.relation = relation

    def __str__(self):
        return "{!r} is an unknown relation type".format(self.relation)


class InvalidRelation(Exception):
    """The relation can't be set between the two objects.

    Attributes
    ----------
    relation: :obj:`str`
        The relation that was given
    parent : :obj:`.scheme.object.ExternalObject`
        The parent object in this relation
    child : :obj:`.scheme.object.ExternalObject`
        The child object in this relation

    """

    def __init__(self, relation, parent, child):
        """Raise when a relation can't be set with this set of objects."""
        self.relation = relation
        self.parent = parent
        self.child = child

    def __str__(self):
        return "{!r} can't be “{}” {!r}".format(self.parent, self.relation, self.child)


class ExternalIDMismatchError(Exception):
    """Raise when two links IDs for the same object/platform mismatch.

    Attributes
    ----------
    link : :obj:`.scheme.object.ObjectLink`
        The existing link on the :obj:`.scheme.object.ExternalObject`
    external_id : str
        The ID that was given

    """

    def __init__(self, link, external_id):
        """Raise with the existing link and the external_id that was given."""
        self.link = link
        self.external_id = external_id

    def __str__(self):
        return "Link {!r} ID does not match {!r}".format(self.link, self.external_id)


class UnknownAttribute(Exception):
    """Raised when an unknown parameter was given.

    Attributes
    ----------
    name : str
        The name of the attribute that was given

    """

    def __init__(self, name):
        """Raise with the name of the attribute given."""
        self.name = name

    def __str__(self):
        return "Unknown attribute {!r}".format(self.name)


class InvalidTransition(Exception):
    """Raised when a state machine transition change fails.

    Attributes
    ----------
    from_state : :obj:`.scheme.utils.CustomEnum`
        The current state
    to_state : :obj:`.scheme.utils.CustomEnum`
        The state that was tried to be set to

    """

    def __init__(self, from_state, to_state):
        self.from_state = from_state
        self.to_state = to_state

    def __str__(self):
        return "Invalid transition from {!r} to {!r}".format(
            self.from_state, self.to_state
        )


class LinkNotFound(Exception):
    """Raise when the scrapped platform has no links in the inserted object.

    Attributes
    ----------
    links : list of :obj:`.scheme.object.ObjectLink`
        The links that exists on the object
    platform : :obj:`.scheme.platform.Platform`
        The platform that was scrapped where the object was found

    """

    def __init__(self, links, platform):
        """Raise with the links on the object and the platform scrapped."""
        self.links = links
        self.platform = platform

    def __str__(self):
        return "Could not find link for {!r} in {!r}".format(self.platform, self.links)


class InvalidMetadata(Exception):
    """The given metadata can't be set for this type.

    Attributes
    ----------
    object_type : :obj:`.scheme.object.ExternalObjectType`
        The type of object being inserted
    key : str
        The metadata that was tried to be added

    """

    def __init__(self, object_type, key):
        """Raise with the type the object is and the metadata key."""
        self.object_type = object_type
        self.key = key

    def __str__(self):
        return "Can't add metadata {!r} in type {!r}".format(self.key, self.object_type)


class InvalidMetadataValue(Exception):
    """The given metadata value is invalid.

    Attributes
    ----------
    key : str
        The key of the metadata
    content : any
        The content of the metadata

    """

    def __init__(self, key, content):
        """Raise with the metadata key and content."""
        self.key = key
        self.content = content

    def __str__(self):
        return "Invalid metadata value {!r} for {!r}".format(self.key, self.content)


class LinksOverlap(Exception):
    """The two objects have links that overlaps.

    Attributes
    ----------
    mine : :obj:`.scheme.object.ExternalObject`
        The object that is being merged
    their : :obj:`.scheme.object.ExternalObject`
        The object it is merged into

    """

    def __init__(self, mine, their):
        """Raise with the two objects being merged."""
        self.mine = mine
        self.their = their

    def __str__(self):
        return "Links in {!r} overlaps with the ones in {!r}".format(
            self.mine, self.their
        )
