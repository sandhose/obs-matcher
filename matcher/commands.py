import sys
from operator import attrgetter

import click


@click.command()
@click.option('--force',
              prompt="This will distroy everything in the "
                     "database, except the platforms. Are you sure?",
              is_flag=True)
def nuke(force=False):
    """Nuke the database"""
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


@click.command()
@click.option('--scrap', '-s', type=int)
@click.option('--platform', '-p')
@click.option('--exclude', '-e')
@click.option('--offset', '-o', type=int)
@click.option('--limit', '-l', type=int)
def match(scrap=None, platform=None, exclude=None, offset=None, limit=None):
    """Try to match ExternalObjects with each other"""
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


@click.command()
@click.option('--threshold', '-t', prompt=True, type=float)
@click.option('--invert', '-i', is_flag=True)
@click.argument('input', type=click.File('r'))
def merge(threshold, invert, input):
    """Merge candidates above a given threshold"""
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


@click.command('import')
@click.option('--platform', '-p', prompt=True)
@click.argument('input', type=click.File('r'))
def import_ids(platform, input):
    """Import links from a CSV file"""
    import csv
    from tqdm import tqdm
    from .app import db
    from .scheme.object import ExternalObject, ObjectLink
    from .scheme.platform import Platform

    has_header = csv.Sniffer().has_header(input.read(1024))
    input.seek(0)
    rows = csv.reader(input, delimiter=',')

    if has_header:
        rows.__next__()

    p = Platform.lookup(platform)

    it = tqdm(rows)
    for row in it:
        id = row[0]
        external_id = row[1]

        obj = ExternalObject.query.get(id)

        if obj is None or not external_id:
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


@click.command('import-attributes')
@click.option('--attribute', '-a', multiple=True, type=(int, str))
@click.option('--platform', '-p', prompt=True)
@click.argument('input', type=click.File('r'))
def import_attribute(attribute, platform, input):
    """Import attributes from a CSV file"""
    import csv
    from tqdm import tqdm
    from .app import db
    from .scheme.platform import Platform
    from .scheme.object import ExternalObject
    from .scheme.value import ValueType

    has_header = csv.Sniffer().has_header(input.read(1024))
    input.seek(0)
    rows = csv.reader(input, delimiter=',')

    if has_header:
        rows.__next__()

    p = Platform.lookup(platform)

    it = tqdm(rows)
    for row in it:
        id = row[0]
        obj = ExternalObject.query.get(id)

        if obj is None:
            it.write('SKIP {}'.format(id))
            continue

        for index, type in attribute:
            type = ValueType.from_name(type)
            values = [t for t in row[index].split(',') if t]
            for value in values:
                obj.add_attribute({
                    'type': type,
                    'text': value
                }, p)

        db.session.commit()


@click.command()
@click.option('--offset', '-o', type=int)
@click.option('--limit', '-l', type=int)
@click.option('--platform', '-p', multiple=True)
@click.option('--type', '-t')
@click.option('--name', '-n')
@click.option('--ignore', '-i', multiple=True)
@click.option('--exclude', '-e', type=click.File('r'))
@click.option('--progress/--no-progress', default=True)
@click.option('--explode/--no-explode', default=False)
@click.option('--with-country/--no-with-country', default=False)
def export(offset=None, limit=None, platform=[], type=None, ignore=[],
           progress=True, explode=False, with_country=False, name=None,
           exclude=None):
    """Export ExternalObjects to CSV"""
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

    query = ExternalObject.query.\
        filter(ExternalObject.type == ExternalObjectType.MOVIE).\
        filter(ExternalObject.id.in_(include_list)).\
        order_by(ExternalObject.id)

    if exclude:
        query = query.filter(~ExternalObject.id.
                             in_([int(line) for line in exclude]))

    it = query[offset:limit]

    if progress:
        it = tqdm(it)

    fieldnames = ['IMDb', 'LUMIERE', 'TMDB', 'Year', 'Films total',
                  'Geo coverage', 'Countries', 'Total European OBS',
                  '100% national productions', 'National co-productions',
                  'Non-National European OBS', 'EU 28',
                  'EU 28 co-productions', 'European OBS co-productions',
                  'International', 'US', 'Other International',
                  'International co-productions', 'US co-productions',
                  'Title', 'SVOD', 'TVOD', 'Platform Country',
                  'Platform Name', 'Scrap ID']

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

        matching_country = next((l.platform.country for l in real_links
                                 if l.platform.country == c1), '')

        # TODO: Clean up this mess
        data = {
            'IMDb': imdb_id,
            'LUMIERE': lumiere_id,
            'TMDB': tmdb_id,
            'Year': date,
            'Films total': len(real_links),
            'Geo coverage': 1 if len(countries) > 0 else 0,
            'Countries': ','.join(countries),
            'Total European OBS': 1 if c1 and c1 in EUROBS else 0,
            '100% national productions': 1 if c1 and matching_country == c1 and not coprod else 0,
            'National co-productions': 1 if c1 and matching_country == c1 and coprod else 0,
            'Non-National European OBS': 1 if c1 and matching_country != c1 and c1 in EUROBS else 0,
            'EU 28': 1 if c1 and c1 in EUR28 else 0,
            'EU 28 co-productions': 1 if c1 and c1 in EUR28 and coprod else 0,
            'European OBS co-productions': 1 if c1 and c1 in EUROBS and coprod else 0,
            'International': 1 if c1 and c1 not in EUROBS else 0,
            'US': 1 if c1 and c1 == 'US' else 0,
            'Other International': 1 if c1 and c1 not in EUROBS + ['US'] else 0,
            'International co-productions': 1 if c1 and c1 not in EUROBS and c1 != 'US' and coprod else 0,
            'US co-productions': 1 if c1 and c1 == 'US' and coprod else 0,
            'Title': title,
            'SVOD': next((1 for p in platform for l in e.links
                          if p.type == PlatformType.SVOD and l.platform == p), 0),
            'TVOD': next((1 for p in platform for l in e.links
                          if p.type == PlatformType.TVOD and
                          l.platform == p), 0),
            'Platform Country': ','.join([link.platform.country
                                          for link in real_links]),
            'Platform Name': name,
            'Scrap ID': e.id
        }

        if explode:
            for link in real_links:
                c = link.platform.country
                type = link.platform.type
                writer.writerow({
                    **data,
                    'Films total': 1,
                    '100% national productions': 1 if c1 and c == c1 and not coprod else 0,
                    'National co-productions': 1 if c1 and c == c1 and coprod else 0,
                    'Non-National European OBS': 1 if c1 and (c != c1 and
                                                              c1 in EUROBS) else 0,
                    'SVOD': 1 if type is PlatformType.SVOD else 0,
                    'TVOD': 1 if type is PlatformType.TVOD else 0,
                    'Platform Country': c,
                    'Platform Name': link.platform.name
                })
        else:
            writer.writerow(data)


def setup_cli(app):
    app.cli.add_command(nuke)
    app.cli.add_command(match)
    app.cli.add_command(merge)
    app.cli.add_command(import_ids)
    app.cli.add_command(import_attribute)
    app.cli.add_command(export)
