from operator import attrgetter

import click
from flask.cli import with_appcontext


class ValueTypeParamType(click.ParamType):
    name = 'type'

    def convert(self, value, param, ctx):
        from .scheme.value import ValueType
        t = ValueType.from_name(value)

        if t is None:
            self.fail('unknown type ' + value, param, ctx)

        return t


class PlatformParamType(click.ParamType):
    name = 'platform'

    @with_appcontext
    def convert(self, value, param, ctx):
        from .scheme.platform import Platform
        p = Platform.lookup(value)

        if p is None:
            self.fail('unknown platform ' + value, param, ctx)

        return p


class PlatformTypeParamType(click.ParamType):
    name = 'type'

    def convert(self, value, param, ctx):
        from .scheme.platform import PlatformType
        p = PlatformType.from_name(value)

        if p is None:
            self.fail('unknown platform type ' + value, param, ctx)

        return p


class ExternalObjectParamType(click.ParamType):
    name = 'type'

    def convert(self, value, param, ctx):
        from .scheme.object import ExternalObjectType
        t = ExternalObjectType.from_name(value)

        if t is None:
            self.fail('unknown type ' + value, param, ctx)

        return t


class ScrapParamType(click.ParamType):
    name = 'scrap id'

    @with_appcontext
    def convert(self, value, param, ctx):
        from .scheme.platform import Scrap
        try:
            s = Scrap.query.get(int(value))
            if s is None:
                self.fail('scrap {} not found'.format(value), param, ctx)
            return s
        except ValueError:
            self.fail('scrap id should be a number', param, ctx)


PLATFORM = PlatformParamType()
PLATFORM_TYPE = PlatformTypeParamType()
SCRAP = ScrapParamType()
VALUE_TYPE = ValueTypeParamType()
EXTERNAL_OBJECT_TYPE = ExternalObjectParamType()


@click.command()
@with_appcontext
@click.confirmation_option(prompt="This will distroy everything in the "
                           "database, except the platforms. Are you sure?")
def nuke():
    """Nuke the database"""
    from .app import db
    for table in ['role', 'person', 'episode', 'scrap_link', 'value_source',
                  'value', 'scrap', 'object_link_work_meta', 'object_link',
                  'external_object']:
        sql = 'TRUNCATE TABLE {} RESTART IDENTITY CASCADE'.format(table)
        click.echo(sql)
        db.session.execute(sql)
    db.session.commit()
    db.session.close()
    click.echo("Done.")


@click.command()
@with_appcontext
@click.option('--scrap', '-s', type=SCRAP)
@click.option('--platform', '-p', type=PLATFORM)
@click.option('--exclude', '-e', type=PLATFORM)
@click.option('--type', '-t', type=EXTERNAL_OBJECT_TYPE)
@click.option('--offset', '-o', type=int)
@click.option('--limit', '-l', type=int)
def match(scrap=None, platform=None, exclude=None, offset=None, type=None, limit=None):
    """Try to match ExternalObjects with each other"""
    from .scheme.platform import Scrap
    from .scheme.object import ExternalObject, ExternalObjectType, \
        ObjectLink, scrap_link
    from .app import db

    db.session.add_all((x for x in [scrap, platform] if x))

    if offset is not None and limit is not None:
        limit = offset + limit

    if type is None:
        type = ExternalObjectType.MOVIE

    q = ObjectLink.query.\
        join(ObjectLink.external_object).\
        filter(ExternalObject.type == type)

    if platform:
        q = q.filter(ObjectLink.platform == platform)
    else:
        if scrap is None:
            scrap = Scrap.query.order_by(Scrap.id.desc()).one()

        q = q.filter(ObjectLink.id.in_(
            db.session.query(scrap_link.c.object_link_id).
            filter(scrap_link.c.scrap_id == scrap.id)
        ))

    if exclude:
        q = q.filter(~ObjectLink.external_object_id.in_(
            db.session.query(ObjectLink.external_object_id)
            .filter(ObjectLink.platform == exclude)
        ))

    objs = [l.external_object for l in q[offset:limit]]
    ExternalObject.match_objects(objs)


@click.command()
@with_appcontext
@click.option('--threshold', '-t', prompt=True, type=float)
@click.option('--invert', '-i', is_flag=True)
@click.option('--interactive/--non-interactive', '-i/-I', default=True)
@click.argument('input', type=click.File('r'))
def merge(threshold, invert, interactive, input):
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

    if interactive:
        click.echo_via_pager('\n'.join([repr(c) for c in candidates]))

    if not interactive or click.confirm('Merge?'):
        ExternalObject.merge_candidates(candidates)


@click.command('import')
@with_appcontext
@click.option('--external-id', '-e', 'external_ids', multiple=True,
              type=(int, PLATFORM))
@click.option('--attribute', '-a', 'attributes', multiple=True,
              type=(int, VALUE_TYPE))
@click.option('--platform', '-p', 'attr_platform', prompt=True, type=PLATFORM)
@click.argument('input', type=click.File('r'))
def import_csv(external_ids, attributes, attr_platform, input):
    """Import data from a CSV file"""
    import csv
    from tqdm import tqdm
    from .app import db
    from .scheme.object import ExternalObject, ObjectLink

    # attr_platform was loaded in another session
    db.session.add_all([attr_platform])

    has_header = csv.Sniffer().has_header(input.read(1024))
    input.seek(0)
    rows = csv.reader(input, delimiter=',')

    if has_header:
        rows.__next__()

    it = tqdm(rows)
    for row in it:
        id = row[0]
        obj = ExternalObject.query.get(id)

        if not obj:
            it.write('SKIP ' + id)
            continue

        for index, type in attributes:
            values = [t for t in row[index].split(',') if t]
            for value in values:
                obj.add_attribute({
                    'type': type,
                    'text': value
                }, attr_platform)

        db.session.commit()

        for index, platform in external_ids:
            external_id = row[index]

            if not external_id:
                it.write('SKIP {} ({})'.format(id, platform.slug))
                continue

            link = ObjectLink.query.\
                filter(ObjectLink.external_id == external_id).first()
            if link is None:
                it.write('LINK {} {} ({})'.format(id, external_id,
                                                  platform.slug))
                obj.links.append(ObjectLink(external_object=obj,
                                            platform=platform,
                                            external_id=external_id))
            elif link.external_object != obj:
                it.write('MERGE {} {}'.format(id, external_id))
                try:
                    link.external_object.merge_and_delete(obj, db.session)
                except Exception as e:
                    it.write(str(e))
            else:
                it.write('ALREADY MERGED {} {} ({})'.format(id, external_id,
                                                            platform.slug))

        db.session.commit()


@click.command('merge-episodes')
@with_appcontext
def merge_episodes():
    """Merge episodes that are in the same serie"""
    from sqlalchemy import and_
    from sqlalchemy.orm import aliased
    from .scheme.object import Episode
    from .app import db

    candidates = set()
    other = aliased(Episode)

    query = db.session.query(Episode.external_object_id, other.external_object_id).\
        join((other, and_(
            Episode.episode == other.episode,
            Episode.season == other.season,
            Episode.serie_id == other.serie_id,
            Episode.external_object_id != other.external_object_id
        ))).\
        filter(Episode.episode is not None and Episode.season is not None)

    candidates = frozenset([
        frozenset([q[0], q[1]]) for q in query
    ])

    for (i, j) in candidates:
        print("{}\t{}\t5.0".format(i, j))


@click.command("fix-countries")
@with_appcontext
def fix_countries():
    """Fix countries attributes with no ISO codes"""
    from sqlalchemy.sql.expression import func
    from .scheme.value import Value, ValueType, ValueSource
    from .app import db
    from .countries import lookup
    from tqdm import tqdm

    values = list(
        Value.query
        .filter(~Value.external_object_id.in_(
            db.session.query(Value.external_object_id)
            .filter(Value.type == ValueType.COUNTRY)
            .filter(func.length(Value.text) == 2)
        ))
        .filter(Value.type == ValueType.COUNTRY)
        .all()
    )

    added = 0

    for v in tqdm(values):
        new = lookup(v.text)
        if new is not None:
            added += 1

            value = Value(type=ValueType.COUNTRY,
                          text=new,
                          external_object_id=v.external_object_id)

            db.session.add(value)

            for source in v.sources:
                value.sources.append(ValueSource(platform=source.platform, score_factor=source.score_factor))
    db.session.commit()
    print("Fixed {} countries out of {}".format(added, len(values)))


@click.command()
@with_appcontext
@click.option('--offset', '-o', type=int)
@click.option('--limit', '-l', type=int)
@click.option('--platform', '-p', multiple=True, type=PLATFORM)
@click.option('--group', '-g', type=PLATFORM_TYPE)
@click.option('--type', '-t', type=EXTERNAL_OBJECT_TYPE)
@click.option('--name', '-n')
@click.option('--ignore', '-i', multiple=True, type=PLATFORM)
@click.option('--exclude', '-e', type=click.File('r'))
@click.option('--progress/--no-progress', default=True)
@click.option('--explode/--no-explode', default=False)
@click.option('--with-country/--no-with-country', default=False)
@click.option('--count-countries/--no-count-countries', default=False)
def export(offset=None, limit=None, platform=[], group=None, ignore=[],
           progress=True, explode=False, with_country=False, name=None,
           exclude=None, type=None, count_countries=False):
    """Export ExternalObjects to CSV"""
    import csv
    import sys
    from tqdm import tqdm
    from .scheme.object import ExternalObject, ObjectLink, \
        ExternalObjectType, Episode
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

    if group:
        platform = Platform.query.\
            filter(Platform.type == group)

    platform_ids = [p.id for p in platform]
    ignore_ids = [p.id for p in ignore]

    ignore_ids += db.session.query(Platform.id).\
        filter(Platform.ignore_in_exports == True).\
        all()

    if platform_ids:
        include_list = include_list.\
            filter(ObjectLink.platform_id.in_(platform_ids))

    if ignore_ids:
        include_list = include_list.\
            filter(~ObjectLink.platform_id.in_(ignore_ids))

    if type is None:
        type = ExternalObjectType.MOVIE

    query = ExternalObject.query.\
        filter(ExternalObject.type == type).\
        filter(ExternalObject.id.in_(include_list)).\
        order_by(ExternalObject.id)

    if exclude:
        query = query.filter(~ExternalObject.id.
                             in_([int(line) for line in exclude]))

    it = query[offset:limit]

    if progress:
        it = tqdm(it)

    fieldnames = ['IMDb', 'LUMIERE/TVDB', 'TMDB', 'Year', 'Total count',
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

    if type == ExternalObjectType.SERIE:
        lumieretvdb = Platform.query.filter(Platform.slug == 'tvdb').one()
    else:
        lumieretvdb = Platform.query.filter(Platform.slug == 'lumiere').one()

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
        lumieretvdb_id = pl_id(lumieretvdb)

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

        def get_real_links(links):
            seen = set()
            for link in links:
                if link.platform_id in platform_ids and \
                   link.platform_id not in seen and \
                   link.platform_id not in ignore_ids:
                    seen.add(link.platform_id)
                    yield link

        real_links = list(get_real_links(e.links))

        links_countries = set([link.platform.country for link in real_links])

        matching_country = next((l.platform.country for l in real_links
                                 if l.platform.country == c1), '')

        if type == ExternalObjectType.SERIE:
            total_count = db.session.query(Episode.episode, Episode.season).\
                filter(Episode.serie == e).\
                join(ObjectLink, ObjectLink.external_object_id == Episode.external_object_id).\
                filter(ObjectLink.platform_id.in_(platform_ids)).\
                group_by(Episode.episode, Episode.season).\
                count()
        else:
            total_count = len(links_countries) if count_countries else len(real_links)

        # TODO: Clean up this mess
        data = {
            'IMDb': imdb_id,
            'LUMIERE/TVDB': lumieretvdb_id,
            'TMDB': tmdb_id,
            'Year': date,
            'Total count': total_count,
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
            'Platform Country': ','.join(links_countries),
            'Platform Name': name,
            'Scrap ID': e.id
        }

        if explode:
            for link in real_links:
                if type == ExternalObjectType.SERIE:
                    total_count = db.session.query(Episode.episode, Episode.season).\
                        filter(Episode.serie == e).\
                        join(ObjectLink, ObjectLink.external_object_id == Episode.external_object_id).\
                        filter(ObjectLink.platform_id == link.platform_id).\
                        count()
                else:
                    total_count = 1

                c = link.platform.country
                ptype = link.platform.type
                writer.writerow({
                    **data,
                    'Total count': total_count,
                    '100% national productions': 1 if c1 and c == c1 and not coprod else 0,
                    'National co-productions': 1 if c1 and c == c1 and coprod else 0,
                    'Non-National European OBS': 1 if c1 and (c != c1 and
                                                              c1 in EUROBS) else 0,
                    'SVOD': 1 if ptype is PlatformType.SVOD else 0,
                    'TVOD': 1 if ptype is PlatformType.TVOD else 0,
                    'Platform Country': c,
                    'Platform Name': link.platform.name
                })
        else:
            writer.writerow(data)


def setup_cli(app):
    app.cli.add_command(nuke)
    app.cli.add_command(match)
    app.cli.add_command(merge)
    app.cli.add_command(merge_episodes)
    app.cli.add_command(import_csv)
    app.cli.add_command(export)
    app.cli.add_command(fix_countries)
