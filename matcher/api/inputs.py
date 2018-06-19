class custom_enum(object):
    def __init__(self, enum):
        self.enum = enum

    def __call__(self, value):
        enum = self.enum.from_name(value)
        if enum is None:
            raise ValueError('{value} is an invalid choice (valid ones are {choices})'
                             .format(value=value,
                                     choices=', '.join((str(e) for e in self.enum))))
        return enum

    def __deepcopy__(self, memo):
        return custom_enum(self.enum)

    @property
    def __schema__(self):
        return {
            'type': 'string',
            'enum': [str(e) for e in self.enum]
        }
