from . import groups, platforms, queue, scraps


def register_all(api):
    api.add_namespace(platforms.api)
    api.add_namespace(groups.api)
    api.add_namespace(scraps.api)
    api.add_namespace(queue.api)
