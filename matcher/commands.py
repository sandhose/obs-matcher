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

    @app.cli.command('import-attribute')
    @click.argument('attribute')
    @click.argument('input', type=click.File('r'))
    def import_attribute(attribute, input):
        # TODO
        pass

    @app.cli.command()
    @click.option('--offset', '-o', type=int)
    @click.option('--limit', '-l', type=int)
    @click.option('--platform', '-p', multiple=True)
    @click.option('--type', '-t')
    @click.option('--ignore', '-i', multiple=True)
    @click.option('--progress/--no-progress', default=True)
    @click.option('--explode/--no-explode', default=False)
    @click.option('--with-country/--no-with-country', default=False)
    def export(offset=None, limit=None, platform=[], type=None, ignore=[],
               progress=True, explode=False, with_country=False):
        import csv
        import sys
        from tqdm import tqdm
        from .scheme.object import ExternalObject, ObjectLink, \
            ExternalObjectType
        from .scheme.platform import Platform, PlatformType
        from .scheme.value import Value, ValueType
        from .app import db

        EUR28 = ['DE', 'AT', 'BE', 'BG', 'CY', 'HR', 'DK', 'ES', 'EE', 'FI',
                 'FR', 'GR', 'HU', 'IE', 'IT', 'LV', 'LT', 'MT', 'LU', 'NL',
                 'PL', 'PT', 'CZ', 'RO', 'GB', 'SK', 'SI', 'SE']
        EUROBS = ['AL', 'AM', 'AT', 'BA', 'BE', 'BG', 'CH', 'CY', 'CZ', 'DE',
                  'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GE', 'GR', 'HR', 'HU',
                  'IE', 'IS', 'IT', 'LI', 'LT', 'LU', 'LV', 'ME', 'MK', 'MT',
                  'NL', 'NO', 'PL', 'PT', 'RO', 'RU', 'SE', 'SI', 'SK', 'TR']

        if offset is not None and limit is not None:
            limit = offset + limit

        include_list = db.session.query(ObjectLink.external_object_id)
        ignore = [Platform.lookup(i).id for i in ignore]
        platform = [Platform.lookup(i) for i in platform]

        if type:
            platform = Platform.query.\
                filter(Platform.type == PlatformType.from_name(type))
        platform_ids = [p.id for p in platform]

        if platform_ids:
            include_list = include_list.\
                filter(ObjectLink.platform_id.in_(platform_ids))

        if ignore:
            include_list = include_list.\
                filter(~ObjectLink.platform_id.in_(ignore))

        it = ExternalObject.query.\
            filter(ExternalObject.type == ExternalObjectType.MOVIE).\
            filter(ExternalObject.id.in_(include_list)).\
            order_by(ExternalObject.id)[offset:limit]

        if progress:
            it = tqdm(it)

        fieldnames = ['IMDb', 'LUMIERE', 'TMDB', 'Year', 'Films total',
                      'Geo coverage', 'Countries', 'Total European',
                      'National European', 'Non-National European OBS',
                      'EU 28', 'EU 28 Co-prod', 'European OBS Co-prod',
                      'Total Non-European', 'US', 'Other Non-European',
                      'Non-European Co-productions', 'US Co-prod', 'Title',
                      'SVOD', 'TVOD', 'Platform Country', 'Scrap ID']

        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()

        imdb = Platform.query.filter(Platform.slug == 'imdb').one()
        tmdb = Platform.query.filter(Platform.slug == 'tmdb').one()
        lumiere = Platform.query.filter(Platform.slug == 'lumiere').one()

        for e in it:
            countries = db.session.query(Value.text).\
                filter(Value.external_object == e).\
                filter(Value.type == ValueType.COUNTRY).\
                order_by(Value.score.desc()).\
                all()

            countries = [c[0] for c in countries if len(c[0]) == 2]
            [c1, c2, c3, *cmore] = countries + ([None] * 4)

            if not c1 and with_country:
                continue

            def pl_id(platform):
                return next((l.external_id for l in e.links
                             if l.platform == platform), None)

            imdb_id = pl_id(imdb)
            tmdb_id = pl_id(tmdb)
            lumiere_id = pl_id(lumiere)

            titles = db.session.query(Value.text).\
                filter(Value.external_object == e).\
                filter(Value.type == ValueType.TITLE).\
                order_by(Value.score.desc()).\
                all()
            title = next((t[0] for t in titles), None)

            dates = db.session.query(Value.text).\
                filter(Value.external_object == e).\
                filter(Value.type == ValueType.DATE).\
                order_by(Value.score.desc()).\
                all()
            date = next((d[0] for d in dates if len(d[0]) == 4), None)

            coprod = len(countries) > 1

            real_links = [link for link in e.links
                          if link.platform_id in platform_ids and
                          link.platform_id not in ignore]

            data = {
                'IMDb': imdb_id,
                'LUMIERE': lumiere_id,
                'TMDB': tmdb_id,
                'Year': date,
                'Films total': len(real_links),
                'Geo coverage': 1 if len(countries) > 0 else 0,
                'Countries': ','.join(countries),
                'Total European': 1 if c1 in EUROBS else 0,
                'National European': 0,
                'Non-National European OBS': 0,
                'EU 28': 1 if c1 in EUR28 else 0,
                'EU 28 Co-prod': 1 if c1 in EUR28 and coprod else 0,
                'European OBS Co-prod': 1 if c1 in EUROBS and coprod else 0,
                'Total Non-European': 1 if c1 not in EUROBS else 0,
                'US': 1 if c1 is 'US' else 0,
                'Other Non-European': 1 if c1 not in EUROBS + ['US'] else 0,
                'Non-European Co-productions': 1 if (c1 not in EUROBS and
                                                     c1 is not 'US' and
                                                     coprod) else 0,
                'US Co-prod': 1 if c1 is 'US' and coprod else 0,
                'Title': title,
                'SVOD': next((1 for p in platform for l in e.links
                              if p.type == PlatformType.SVOD and
                              l.platform == p), 0),
                'TVOD': next((1 for p in platform for l in e.links
                              if p.type == PlatformType.TVOD and
                              l.platform == p), 0),
                'Platform Country': next((p.country
                                          for p in platform
                                          for l in e.links
                                          if p.type == PlatformType.TVOD and
                                          l.platform == p), None),
                'Scrap ID': e.id
            }

            if explode:
                for link in real_links:
                    c = link.platform.country
                    type = link.platform.type
                    writer.writerow({
                        **data,
                        'National European': 1 if c is c1 else 0,
                        'Non-National European OBS': 1 if (c is not c1 and
                                                           c1 in EUROBS) else 0,
                        'SVOD': 1 if type is PlatformType.SVOD else 0,
                        'TVOD': 1 if type is PlatformType.TVOD else 0,
                        'Platform Country': c,
                    })
            else:
                writer.writerow(data)
