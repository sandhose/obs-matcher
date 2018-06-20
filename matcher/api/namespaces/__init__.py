from . import groups, platforms, scraps, queue


def register_all(api):
    api.add_namespace(platforms.api)
    api.add_namespace(groups.api)
    api.add_namespace(scraps.api)
    api.add_namespace(queue.api)
