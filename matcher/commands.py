import contextlib
from operator import itemgetter

from flask import url_for
from flask_script import Command


class RoutesCommand(Command):
    """List registered routes"""

    def __init__(self, app):
        self.app = app

    def run(self):
        from urllib.parse import unquote
        output = []
        for rule in self.app.url_map.iter_rules():

            options = {}
            for arg in rule.arguments:
                options[arg] = "[{0}]".format(arg)

            methods = ','.join(rule.methods)
            url = url_for(rule.endpoint, **options)
            line = unquote("{:35s} {:35s} {}"
                           .format(rule.endpoint, methods, url))
            output.append((line, url))

        # Sort output by url not name
        for (line, _) in sorted(output, key=itemgetter(1)):
            print(line)


class NukeCommand(Command):
    """Nuke the database (except the platform table)"""

    def __init__(self, db):
        self.db = db

    def run(self):
        with contextlib.closing(self.db.engine.connect()) as con:
            trans = con.begin()
            for table in reversed(self.db.metadata.sorted_tables):
                if table.name != 'platform':
                    con.execute(table.delete())
            trans.commit()
