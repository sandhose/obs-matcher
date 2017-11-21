import sys
import click
from operator import itemgetter, attrgetter

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
    @click.option('--platform', '-p')
    @click.option('--offset', '-o', type=int)
    @click.option('--limit', '-l', type=int)
    def match(scrap=None, platform=None, offset=None, limit=None):
        from .scheme.platform import Scrap, Platform
        from .scheme.object import ExternalObject

        if offset is not None and limit is not None:
            limit = offset + limit

        if platform is not None:

            p = Platform.lookup(platform)
            objs = [l.external_object for l in p.links[offset:limit]]
            ExternalObject.match_objects(objs)
            return

        if scrap is not None:
            scrap = Scrap.query.filter(Scrap.id == scrap).first()
        else:
            scrap = Scrap.query.order_by(Scrap.id.desc()).first()

        if scrap is None:
            click.echo("Scrap not found")
            sys.exit(1)

        objs = [l.external_object for l in scrap.links[offset:limit]]
        ExternalObject.match_objects(objs)

    @app.cli.command()
    @click.option('--threshold', '-t', prompt=True, type=float)
    @click.option('--invert', '-i', is_flag=True)
    @click.argument('input', type=click.File('r'))
    def merge(threshold, invert, input):
        from .scheme.object import MergeCandidate, ExternalObject
        lines = input.readlines()

        candidates = []

        for line in lines:
            src, dest, score = line.split('\t')
            if invert:
                src, dest = dest, src

            candidate = MergeCandidate(obj=int(src), into=int(dest),
                                       score=float(score))
            if candidate.score >= threshold:
                candidates.append(candidate)

        candidates = sorted(candidates, key=attrgetter('score'), reverse=True)

        for c in candidates:
            print(c)

        if click.confirm('Merge?'):
            ExternalObject.merge_candidates(candidates)
