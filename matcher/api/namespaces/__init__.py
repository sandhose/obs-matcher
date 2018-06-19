from . import groups, platforms, scraps


def register_all(api):
    api.add_namespace(platforms.api)
    api.add_namespace(groups.api)
    api.add_namespace(scraps.api)
