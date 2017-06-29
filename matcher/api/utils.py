from restless.preparers import Preparer, FieldsPreparer


class SubOrNullPreparer(Preparer):
    def __init__(self, preparer):
        self.preparer = preparer

    def prepare(self, data):
        if data is None:
            return None
        else:
            return self.preparer.prepare(data)


class AutoPreparer(Preparer):
    def __init__(self, fields):
        f = {
            'id': 'id',
            'self': 'self_link'
        }

        for k, v in fields.items():
            f[k] = v

        self.preparer = SubOrNullPreparer(FieldsPreparer(fields=f))

    def prepare(self, data):
        return self.preparer.prepare(data)
