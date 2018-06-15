from . import groups, platforms


def register_all(api):
    api.add_namespace(platforms.api)
    api.add_namespace(groups.api)
