import json

from restless.fl import FlaskResource
from restless.preparers import FieldsPreparer, Preparer
from restless.serializers import JSONSerializer, MoreTypesJSONEncoder

from ..scheme.utils import CustomEnum


class CustomJSONEncoder(MoreTypesJSONEncoder):
    """A JSON encode that also encodes CustomEnum"""

    def default(self, data):
        if isinstance(data, CustomEnum):
            return data.__str__()
        else:
            return super(CustomJSONEncoder, self).default(data)


class CustomSerializer(JSONSerializer):
    """A custom serializer that uses the CustomJSONEncoder"""

    def serialize(self, data):
        return json.dumps(data, cls=CustomJSONEncoder)


class CustomFlaskResource(FlaskResource):
    """A restless resource that uses CustomSerializer"""

    serializer = CustomSerializer()

    def handle_error(self, err):
        if not hasattr(err, 'status'):
            raise err

        return self.build_error(err)


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
