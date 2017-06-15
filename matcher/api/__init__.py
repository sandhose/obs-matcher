from ..scheme import Platform, PlatformGroup, Scrap
from .platform import PlatformGroupResource, PlatformResource, ScrapResource


def setup_api(app):
    Platform.register_api(app, 'platforms/', PlatformResource)
    PlatformGroup.register_api(app, 'groups/', PlatformGroupResource)
    Scrap.register_api(app, 'scraps/', ScrapResource)
