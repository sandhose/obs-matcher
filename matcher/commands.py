import sys
import click
from operator import itemgetter

from flask import url_for


# TODO: this is ugly
def setup_cli(app):

    # FIXME: doesn't work
    @app.cli.command()
    def routes():
        from urllib.parse import unquote
        output = []
        for rule in app.url_map.iter_rules():

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
            click.echo(line)

    @app.cli.command()
    @click.option('--force',
                  prompt="This will distroy everything in the "
                         "database, except the platforms. Are you sure?",
                  is_flag=True)
    def nuke(force=False):
        from .app import db
        if force:
            for table in ['role', 'person', 'episode', 'season',
                          'scrap_link', 'value_source', 'value', 'scrap',
                          'object_link_work_meta', 'object_link',
                          'external_object']:
                sql = 'TRUNCATE TABLE {} RESTART IDENTITY CASCADE'.format(table)
                click.echo(sql)
                db.session.execute(sql)
            db.session.commit()
            db.session.close()
            click.echo("Done.")
        else:
            click.echo("Aborted.")

    @app.cli.command()
    @click.option('--scrap', '-s', type=int)
    def match(scrap=None):
        from .scheme.platform import Scrap
        if scrap is None:
            scrap = Scrap.query.order_by(Scrap.id.desc()).first()
        else:
            scrap = Scrap.query.filter(Scrap.id == scrap).first()

        if scrap is None:
            click.echo("Scrap not found")
            sys.exit(1)

        scrap.match_objects()
