import enum


class CustomEnum(enum.Enum):
    """A custom enum with serialization/deserialization methods"""

    def __str__(self):
        return self.name.lower()

    @classmethod
    def from_name(cls, name):
        return getattr(cls, name.upper(), None)
