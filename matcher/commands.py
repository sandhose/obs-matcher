import sys
from operator import attrgetter, itemgetter

import click
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
    @click.option('--exclude', '-e')
    @click.option('--offset', '-o', type=int)
    @click.option('--limit', '-l', type=int)
    def match(scrap=None, platform=None, exclude=None, offset=None, limit=None):
        from .scheme.platform import Scrap, Platform
        from .scheme.object import ExternalObject, ExternalObjectType, \
            ObjectLink, scrap_link
        from .app import db

        if offset is not None and limit is not None:
            limit = offset + limit

        q = ObjectLink.query.\
            join(ObjectLink.external_object).\
            filter(ExternalObject.type == ExternalObjectType.MOVIE)

        if platform:
            p = Platform.lookup(platform)
            q = q.filter(ObjectLink.platform == p)
        else:
            if scrap is not None:
                scrap = Scrap.query.filter(Scrap.id == scrap).first()
            else:
                scrap = Scrap.query.order_by(Scrap.id.desc()).first()

            if scrap is None:
                click.echo("Scrap not found")
                sys.exit(1)

            q = q.filter(ObjectLink.id.in_(
                db.session.query(scrap_link.c.object_link_id).
                filter(scrap_link.c.scrap_id == scrap.id)
            ))

        if exclude:
            e = Platform.lookup(exclude)
            q = q.filter(~ObjectLink.external_object_id.in_(
                db.session.query(ObjectLink.external_object_id)
                .filter(ObjectLink.platform == e)
            ))

        objs = [l.external_object for l in q[offset:limit]]
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

    @app.cli.command('import')
    @click.option('--platform', '-p', prompt=True)
    @click.argument('input', type=click.File('r'))
    def import_ids(platform, input):
        import csv
        from tqdm import tqdm
        from .app import db
        from .scheme.object import ExternalObject, ObjectLink
        from .scheme.platform import Platform

        rows = csv.reader(input, delimiter=',')
        p = Platform.lookup(platform)

        it = tqdm(rows)
        for row in it:
            id = row[0]
            external_id = row[1]

            obj = ExternalObject.query.get(id)

            if obj is None:
                it.write('SKIP {} {}'.format(id, external_id))
                continue

            link = ObjectLink.query.\
                filter(ObjectLink.external_id == external_id).first()
            if link is None:
                it.write('LINK {} {}'.format(id, external_id))
                obj.links.append(ObjectLink(external_object=obj,
                                            platform=p,
                                            external_id=external_id))
            elif link.external_object != obj:
                it.write('MERGE {} {}'.format(id, external_id))
                try:
                    obj.merge_and_delete(link.external_object, db.session)
                except Exception as e:
                    it.write(str(e))
            else:
                it.write('ALREADY MERGED {} {}'.format(id, external_id))

            db.session.commit()

    @app.cli.command()
    @click.option('--offset', '-o', type=int)
    @click.option('--limit', '-l', type=int)
    @click.option('--ignore', '-i', multiple=True)
    def export(offset=None, limit=None, ignore=[]):
        import csv
        import sys
        from tqdm import tqdm
        from .scheme.object import ExternalObject, ObjectLink, \
            ExternalObjectType, Role, RoleType
        from .scheme.platform import Platform
        from .scheme.value import Value, ValueType
        from .app import db

        if offset is not None and limit is not None:
            limit = offset + limit

        ignore = [Platform.lookup(i).id for i in ignore]
        include_list = db.session.query(ObjectLink.external_object_id).\
            filter(~ObjectLink.platform_id.in_(ignore))

        it = ExternalObject.query.\
            filter(ExternalObject.type == ExternalObjectType.MOVIE).\
            filter(ExternalObject.id.in_(include_list)).\
            order_by(ExternalObject.id)[offset:limit]
        it = tqdm(it)

        fieldnames = ['id', 'imdb', 'titles', 'countries', 'date', 'genres',
                      'duration', 'directors', 'links']
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)

        imdb = Platform.query.filter(Platform.slug == 'imdb').one()
        for e in it:
            imdb_id = db.session.query(ObjectLink.external_id).\
                filter(ObjectLink.platform == imdb).\
                filter(ObjectLink.external_object == e).\
                limit(1).\
                scalar()

            titles = db.session.query(Value.text).\
                filter(Value.external_object == e).\
                filter(Value.type == ValueType.TITLE).\
                order_by(Value.score.desc()).\
                all()
            titles = [t[0] for t in titles]

            countries = db.session.query(Value.text).\
                filter(Value.external_object == e).\
                filter(Value.type == ValueType.COUNTRY).\
                order_by(Value.score.desc()).\
                all()

            countries = [c[0] for c in countries if len(c[0]) == 2]

            genres = db.session.query(Value.text).\
                filter(Value.external_object == e).\
                filter(Value.type == ValueType.GENRES).\
                order_by(Value.score.desc()).\
                all()
            genres = [g[0] for g in genres]

            durations = db.session.query(Value.text).\
                filter(Value.external_object == e).\
                filter(Value.type == ValueType.DURATION).\
                order_by(Value.score.desc()).\
                all()

            duration = next((d[0] for d in durations
                             if d[0].replace('.', '').isdigit()), None)

            dates = db.session.query(Value.text).\
                filter(Value.external_object == e).\
                filter(Value.type == ValueType.DATE).\
                order_by(Value.score.desc()).\
                all()
            date = next((d[0] for d in dates if len(d[0]) == 4), None)

            directors = db.session.query(Value.text).\
                join(Role, Role.person_id == Value.external_object_id).\
                filter(Role.external_object_id == e.id).\
                filter(Role.role == RoleType.DIRECTOR).\
                filter(Value.type == ValueType.NAME)

            directors = set([d[0].title() for d in directors])

            links = len(e.links)

            writer.writerow(dict(
                id=e.id,
                imdb=imdb_id or '',
                titles='|||'.join(titles),
                genres=','.join(genres),
                countries=','.join(countries),
                date=date or '',
                duration=duration or '',
                directors=','.join(directors),
                links=links,
            ))
