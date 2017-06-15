from ..scheme import Platform, PlatformGroup, Scrap, ValueID, Value
from .platform import PlatformGroupResource, PlatformResource, ScrapResource
from .value import ValueIDResource, ValueResource


def setup_api(app):
    Platform.register_api(app, 'platforms/', PlatformResource)
    PlatformGroup.register_api(app, 'groups/', PlatformGroupResource)
    Scrap.register_api(app, 'scraps/', ScrapResource)

    ValueID.register_api(app, 'value_ids/', ValueIDResource)
    Value.register_api(app, 'values/', ValueResource)
