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
        from matcher.app import db
        p = Platform.lookup(db.session, value)

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
        from matcher.app import db
        try:
            s = db.session.query(Scrap).get(int(value))
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


@click.command(context_settings=dict(
    ignore_unknown_options=True,
))
@click.argument('celery_options', nargs=-1)
def worker(celery_options):
    from matcher import celery
    celery.worker_main(['matcher worker'] + list(celery_options))


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
@click.option('--all/--not-all', '-a/-A', default=False)
def match(scrap=None, platform=None, exclude=None, offset=None, type=None, limit=None, all=False):
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

    q = db.session.query(ExternalObject).\
        filter(ExternalObject.type == type)

    if platform:
        q = q.filter(ExternalObject.id.in_(db.session.query(ObjectLink.external_object_id).
                                           filter(ObjectLink.platform == platform)))
    elif not all:
        if scrap is None:
            scrap = db.session.query(Scrap).order_by(Scrap.id.desc()).one()

        q = q.filter(ExternalObject.id.in_(
            db.session.query(ObjectLink.external_object_id).
            select_from(scrap_link).
            join(ObjectLink, ObjectLink.id == scrap_link.c.object_link_id).
            filter(scrap_link.c.scrap_id == scrap.id)
        ))

    if exclude:
        q = q.filter(~ExternalObject.id.in_(
            db.session.query(ObjectLink.external_object_id)
            .filter(ObjectLink.platform == exclude)
        ))

    objs = q[offset:limit]
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
    from .scheme.value import ValueSource, Value

    # attr_platform was loaded in another session
    db.session.add_all([attr_platform])
    db.session.add_all([platform for _, platform in external_ids])

    # FIXME: the sniffer can behave weirdly if the input stops inside quotes
    has_header = csv.Sniffer().has_header(input.read(1024))
    input.seek(0)
    rows = csv.reader(input, delimiter=',')

    if has_header:
        print('SKIPPING HEADER')
        rows.__next__()

    it = tqdm(rows)
    for row in it:
        id = row[0]
        obj = db.session.query(ExternalObject).get(id)

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
                it.write('> SKIP {} ({})'.format(id, platform.slug))
                continue

            if not platform.allow_links_overlap:
                existing = db.session.query(ObjectLink).\
                    filter(ObjectLink.external_object == obj).\
                    filter(ObjectLink.platform == platform).\
                    first()

                if existing is not None and existing.external_id != external_id:
                    it.write('> DEL old link {}'.format(existing.external_id))

                    # Lookup for old attributes from this source and delete them
                    db.session.query(ValueSource).\
                        filter(ValueSource.id_platform == platform.id).\
                        filter(ValueSource.id_value.in_(
                            db.session.query(Value.id).
                            filter(Value.external_object_id == obj.id)
                        )).\
                        delete(synchronize_session=False)

                    # Remove attributes with no sources
                    db.session.query(Value).\
                        filter(Value.external_object_id == obj.id).\
                        filter(~Value.sources.any()).\
                        delete(synchronize_session=False)

                    db.session.delete(existing)
                    db.session.commit()

            link = db.session.query(ObjectLink).\
                filter(ObjectLink.external_id == external_id).\
                filter(ObjectLink.platform == platform).\
                first()

            if link is None:
                it.write('> LINK {} {} ({})'.format(id, external_id,
                                                    platform.slug))
                obj.links.append(ObjectLink(external_object=obj,
                                            platform=platform,
                                            external_id=external_id))
            elif link.external_object != obj:
                it.write('> MERGE {} {}'.format(id, external_id))

                try:
                    link.external_object.merge_and_delete(obj, db.session)
                except Exception as e:
                    it.write(str(e))
            else:
                it.write('> ALREADY MERGED {} {} ({})'.format(id, external_id,
                                                              platform.slug))

        db.session.commit()


@click.command('merge-episodes')
@with_appcontext
def merge_episodes():
    """Merge episodes that are in the same series"""
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
            Episode.series_id == other.series_id,
            Episode.external_object_id != other.external_object_id
        ))).\
        filter(Episode.episode is not None and Episode.season is not None)

    candidates = frozenset([
        frozenset([q[0], q[1]]) for q in query
    ])

    for (i, j) in candidates:
        print("{}\t{}\t5.0".format(i, j))


@click.command("fix-attributes")
@with_appcontext
def fix_attributes():
    """Fix duplicate attributes"""
    from sqlalchemy.orm import aliased
    from .scheme.value import Value, ValueSource
    from .app import db
    from tqdm import tqdm

    v1 = aliased(Value)
    v2 = aliased(Value)

    values = list(
        db.session.query(v1, v2).
        filter(v1.external_object_id == v2.external_object_id).
        filter(v1.type == v2.type).
        filter(v1.text == v2.text).
        filter(v1.id != v2.id)
    )

    done = set()

    for (v1, v2) in tqdm(values):
        if v1.id in done or v2.id in done:
            continue

        for s2 in v2.sources:
            if not any(s1.platform == s2.platform for s1 in v1.sources):
                v1.sources.append(ValueSource(platform=s2.platform,
                                              score_factor=s2.score_factor))
            db.session.delete(s2)
        done.add(v2.id)

        db.session.delete(v2)
        db.session.commit()


@click.command("fix-titles")
@with_appcontext
def fix_titles():
    """Fix countries attributes with no ISO codes"""
    import re
    from .scheme.value import Value, ValueType, ValueSource
    from .app import db
    from tqdm import tqdm

    values = list(
        db.session.query(Value)
        .filter(Value.text.like('%[%]'))
        .filter(Value.type == ValueType.TITLE)
        .all()
    )

    added = 0

    for v in tqdm(values):
        new = re.sub(r"\[.*\]", "", v.text).strip()

        existing = db.session.query(Value).filter(Value.type == ValueType.TITLE,
                                                  Value.text == new,
                                                  Value.external_object_id == v.external_object_id).first()

        if existing is None:
            added += 1
            value = Value(type=ValueType.TITLE,
                          text=new,
                          external_object_id=v.external_object_id)

            db.session.add(value)

            for source in v.sources:
                value.sources.append(ValueSource(platform=source.platform, score_factor=source.score_factor))

    db.session.commit()
    print("Fixed {} titles out of {}".format(added, len(values)))


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
        db.session.query(Value)
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


@click.command()  # noqa: C901
@with_appcontext
@click.option('--offset', '-o', type=int)
@click.option('--limit', '-l', type=int)
@click.option('--platform', '-p', multiple=True, type=PLATFORM)
@click.option('--cap', '-c', type=PLATFORM)
@click.option('--group', '-g', type=PLATFORM_TYPE)
@click.option('--type', '-t', type=EXTERNAL_OBJECT_TYPE)
@click.option('--name', '-n')
@click.option('--ignore', '-i', multiple=True, type=PLATFORM)
@click.option('--exclude', '-e', type=click.File('r'))
@click.option('--progress/--no-progress', default=True)
@click.option('--explode/--no-explode', default=False)
@click.option('--with-country/--no-with-country', default=False)
@click.option('--count-countries/--no-count-countries', default=False)
def export(offset=None, limit=None, platform=[], cap=None, group=None,
           ignore=[], progress=True, explode=False, with_country=False,
           name=None, exclude=None, type=None, count_countries=False):
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
        platform = db.session.query(Platform).\
            filter(Platform.type == group)

    platform_ids = [p.id for p in platform]
    ignore_ids = [p.id for p in ignore]

    ignore_ids += [id for (id,) in db.session.query(Platform.id).
                   filter(Platform.ignore_in_exports._is(True)).
                   all()]

    if platform_ids:
        include_list = include_list.\
            filter(ObjectLink.platform_id.in_(platform_ids))

    if ignore_ids:
        include_list = include_list.\
            filter(~ObjectLink.platform_id.in_(ignore_ids))

    if type is None:
        type = ExternalObjectType.MOVIE

    query = db.session.query(ExternalObject).\
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

    def generate_flags(total_count, countries, national_production):
        [country, *_] = countries + [None]
        coprod = len(countries) > 1

        def flag(f):
            return total_count if f else 0

        def cflag(f):
            return flag(country is not None and f)

        return {
            'Total count': total_count,
            'Geo coverage': 1 if len(countries) > 0 else 0,
            'Countries': ','.join(countries),
            'Total European OBS': cflag(country in EUROBS),
            '100% national productions': cflag(national_production and not coprod),
            'National co-productions': cflag(national_production and coprod),
            'Non-National European OBS': cflag(not national_production and country in EUROBS),
            'EU 28': cflag(country in EUR28),
            'EU 28 co-productions': cflag(country in EUR28 and coprod),
            'European OBS co-productions': cflag(country in EUROBS and coprod),
            'International': cflag(country not in EUROBS),
            'US': cflag(country == 'US'),
            'Other International': cflag(country not in (EUROBS + ['US'])),
            'International co-productions': cflag(country not in (EUROBS + ['US']) and coprod),
            'US co-productions': cflag(country == 'US' and coprod),
        }

    writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
    writer.writeheader()

    imdb = db.session.query(Platform).filter(Platform.slug == 'imdb').one()
    tmdb = db.session.query(Platform).filter(Platform.slug == 'tmdb').one()

    if type == ExternalObjectType.SERIES:
        lumieretvdb = db.session.query(Platform).filter(Platform.slug == 'tvdb').one()
    else:
        lumieretvdb = db.session.query(Platform).filter(Platform.slug == 'lumiere').one()

    for e in it:
        countries = db.session.query(Value.text).\
            filter(Value.external_object == e).\
            filter(Value.type == ValueType.COUNTRY).\
            order_by(Value.score.desc()).\
            all()

        countries = [c[0] for c in countries if len(c[0]) == 2]
        [country, *_] = countries + [None]

        if not country and with_country:
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

        national_production = any(l.platform.country for l in real_links
                                  if l.platform.country == country)

        if type == ExternalObjectType.SERIES:
            # FIXME: should count_countries do something for seriess?
            total_count = db.session.query(Episode.episode, Episode.season).\
                filter(Episode.series == e).\
                join(ObjectLink, ObjectLink.external_object_id == Episode.external_object_id).\
                filter(ObjectLink.platform_id.in_(platform_ids)).\
                group_by(Episode.episode, Episode.season).\
                count()

            if cap is not None:
                capped_count = db.session.query(Episode.episode, Episode.season).\
                    filter(Episode.series == e).\
                    join(ObjectLink, ObjectLink.external_object_id == Episode.external_object_id).\
                    filter(ObjectLink.platform_id == cap.id).\
                    group_by(Episode.episode, Episode.season).\
                    count()

                if capped_count > 0 and capped_count < total_count:
                    total_count = capped_count
        else:
            total_count = len(links_countries) if count_countries else len(real_links)

        if total_count == 0:
            continue

        # TODO: Clean up this mess
        data = {
            **generate_flags(total_count, countries, national_production),
            'IMDb': imdb_id,
            'LUMIERE/TVDB': lumieretvdb_id,
            'TMDB': tmdb_id,
            'Year': date,
            'Title': title,
            'SVOD': next((total_count for p in platform for l in e.links
                          if p.type == PlatformType.SVOD and l.platform == p), 0),
            'TVOD': next((total_count for p in platform for l in e.links
                          if p.type == PlatformType.TVOD and l.platform == p), 0),
            'Platform Country': ','.join(links_countries),
            'Platform Name': name,
            'Scrap ID': e.id
        }

        if explode:
            for link in real_links:
                if type == ExternalObjectType.SERIES:
                    total_count = db.session.query(ObjectLink.platform_id, ObjectLink.external_object_id).\
                        select_from(Episode).\
                        filter(Episode.series == e).\
                        join(ObjectLink, ObjectLink.external_object_id == Episode.external_object_id).\
                        filter(ObjectLink.platform_id == link.platform_id).\
                        group_by(ObjectLink.platform_id, ObjectLink.external_object_id).\
                        count()

                    if cap is not None and capped_count > 0 and capped_count < total_count:
                        total_count = capped_count
                else:
                    total_count = 1

                if total_count == 0:
                    continue

                national_production = link.platform.country == country
                writer.writerow({
                    **data,
                    **generate_flags(total_count, countries, national_production),
                    'Total count': total_count,
                    'SVOD': total_count if link.platform.type is PlatformType.SVOD else 0,
                    'TVOD': total_count if link.platform.type is PlatformType.TVOD else 0,
                    'Platform Country': link.platform.country,
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
    app.cli.add_command(fix_attributes)
    app.cli.add_command(fix_countries)
    app.cli.add_command(fix_titles)
    app.cli.add_command(worker)
