from datetime import datetime
from operator import attrgetter
from pathlib import Path

import click
from flask.cli import with_appcontext

from matcher.scheme.enums import (
    ExternalObjectType,
    PlatformType,
    ScrapStatus,
    ValueType,
)


class ValueTypeParamType(click.ParamType):
    name = "type"

    def convert(self, value, param, ctx):
        from .scheme.enums import ValueType

        t = ValueType.from_name(value)

        if t is None:
            self.fail("unknown type " + value, param, ctx)

        return t


class SessionParamType(click.ParamType):
    name = "session"

    @with_appcontext
    def convert(self, value, param, ctx):
        from .scheme.platform import Session
        from matcher.app import db

        try:
            s = db.session.query(Session).get(int(value))
        except ValueError:
            s = db.session.query(Session).filter(Session.name.ilike(value)).first()

        if s is None:
            self.fail("session {} not found".format(value), param, ctx)
        return s


class PlatformParamType(click.ParamType):
    name = "platform"

    @with_appcontext
    def convert(self, value, param, ctx):
        from .scheme.platform import Platform
        from matcher.app import db

        p = Platform.lookup(db.session, value)

        if p is None:
            self.fail("unknown platform " + value, param, ctx)

        return p


class ScrapStatusParamType(click.ParamType):
    name = "status"

    def convert(self, value, param, ctx):
        s = ScrapStatus.from_name(value)

        if s is None:
            self.fail("unknown scrap status " + value, param, ctx)

        return s


class PlatformTypeParamType(click.ParamType):
    name = "type"

    def convert(self, value, param, ctx):
        p = PlatformType.from_name(value)

        if p is None:
            self.fail("unknown platform type " + value, param, ctx)

        return p


class ExternalObjectParamType(click.ParamType):
    name = "type"

    def convert(self, value, param, ctx):
        t = ExternalObjectType.from_name(value)

        if t is None:
            self.fail("unknown type " + value, param, ctx)

        return t


class ScrapParamType(click.ParamType):
    name = "scrap id"

    @with_appcontext
    def convert(self, value, param, ctx):
        from .scheme.platform import Scrap
        from matcher.app import db

        try:
            s = db.session.query(Scrap).get(int(value))
            if s is None:
                self.fail("scrap {} not found".format(value), param, ctx)
            return s
        except ValueError:
            self.fail("scrap id should be a number", param, ctx)


PLATFORM = PlatformParamType()
PLATFORM_TYPE = PlatformTypeParamType()
SCRAP = ScrapParamType()
SCRAP_STATUS = ScrapStatusParamType()
SESSION = SessionParamType()
VALUE_TYPE = ValueTypeParamType()
EXTERNAL_OBJECT_TYPE = ExternalObjectParamType()


@click.command(context_settings=dict(ignore_unknown_options=True))
@click.argument("celery_options", nargs=-1)
def worker(celery_options):
    from matcher import celery

    celery.worker_main(["matcher worker"] + list(celery_options))


@click.command()
@with_appcontext
@click.confirmation_option(
    prompt="This will distroy everything in the "
    "database, except the platforms. Are you sure?"
)
def nuke():
    """Nuke the database"""
    from .app import db

    for table in [
        "role",
        "person",
        "episode",
        "scrap_link",
        "value_source",
        "value",
        "scrap",
        "object_link",
        "external_object",
    ]:
        sql = "TRUNCATE TABLE {} RESTART IDENTITY CASCADE".format(table)
        click.echo(sql)
        db.session.execute(sql)
    db.session.commit()
    db.session.close()
    click.echo("Done.")


@click.command()
@with_appcontext
@click.option("--scrap", "-s", type=SCRAP)
@click.option("--platform", "-p", type=PLATFORM)
@click.option("--exclude", "-e", type=PLATFORM)
@click.option("--type", "-t", type=EXTERNAL_OBJECT_TYPE)
@click.option("--offset", "-o", type=int)
@click.option("--limit", "-l", type=int)
@click.option("--all/--not-all", "-a/-A", default=False)
def match(
    scrap=None,
    platform=None,
    exclude=None,
    offset=None,
    type=None,
    limit=None,
    all=False,
):
    """Try to match ExternalObjects with each other"""
    from .scheme.platform import Scrap
    from .scheme.object import ExternalObject, ObjectLink, scrap_link
    from .app import db

    db.session.add_all((x for x in [scrap, platform] if x))

    if offset is not None and limit is not None:
        limit = offset + limit

    if type is None:
        type = ExternalObjectType.MOVIE

    q = db.session.query(ExternalObject).filter(ExternalObject.type == type)

    if platform:
        q = q.filter(
            ExternalObject.id.in_(
                db.session.query(ObjectLink.external_object_id).filter(
                    ObjectLink.platform == platform
                )
            )
        )
    elif not all:
        if scrap is None:
            scrap = db.session.query(Scrap).order_by(Scrap.id.desc()).one()

        q = q.filter(
            ExternalObject.id.in_(
                db.session.query(ObjectLink.external_object_id)
                .select_from(scrap_link)
                .join(ObjectLink, ObjectLink.id == scrap_link.c.object_link_id)
                .filter(scrap_link.c.scrap_id == scrap.id)
            )
        )

    if exclude:
        q = q.filter(
            ~ExternalObject.id.in_(
                db.session.query(ObjectLink.external_object_id).filter(
                    ObjectLink.platform == exclude
                )
            )
        )

    objs = q[offset:limit]
    ExternalObject.match_objects(objs)


@click.command()
@with_appcontext
@click.option("--threshold", "-t", prompt=True, type=float)
@click.option("--invert", "-v", is_flag=True)
@click.option("--interactive/--non-interactive", "-i/-I", default=True)
@click.argument("input", type=click.File("r"))
def merge(threshold, invert, interactive, input):
    """Merge candidates above a given threshold"""
    from .scheme.object import MergeCandidate, ExternalObject

    lines = input.readlines()

    candidates = []

    for line in lines:
        src, dest, score = line.split("\t")
        if invert:
            src, dest = dest, src

        candidate = MergeCandidate(obj=int(src), into=int(dest), score=float(score))
        if candidate.score >= threshold:
            candidates.append(candidate)

    candidates = sorted(candidates, key=attrgetter("score"), reverse=True)

    if interactive:
        click.echo_via_pager("\n".join([repr(c) for c in candidates]))

    if not interactive or click.confirm("Merge?"):
        ExternalObject.merge_candidates(candidates)


@click.command("import")
@with_appcontext
@click.option(
    "--external-id", "-e", "external_ids", multiple=True, type=(int, PLATFORM)
)
@click.option("--attribute", "-a", "attributes", multiple=True, type=(int, VALUE_TYPE))
@click.option("--platform", "-p", "attr_platform", prompt=True, type=PLATFORM)
@click.argument("input", type=click.File("r"))
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
    rows = csv.reader(input, delimiter=",")

    if has_header:
        print("SKIPPING HEADER")
        rows.__next__()

    it = tqdm(rows)
    for row in it:
        id = row[0]
        obj = db.session.query(ExternalObject).get(id)

        if not obj:
            it.write("SKIP " + id)
            continue

        for index, type in attributes:
            values = [t for t in row[index].split(",") if t]
            for value in values:
                obj.add_attribute({"type": type, "text": value}, attr_platform)

        db.session.commit()

        for index, platform in external_ids:
            external_id = row[index]

            if not external_id:
                it.write("> SKIP {} ({})".format(id, platform.slug))
                continue

            if not platform.allow_links_overlap:
                existing = (
                    db.session.query(ObjectLink)
                    .filter(ObjectLink.external_object == obj)
                    .filter(ObjectLink.platform == platform)
                    .first()
                )

                if existing is not None and existing.external_id != external_id:
                    it.write("> DEL old link {}".format(existing.external_id))

                    # Lookup for old attributes from this source and delete them
                    db.session.query(ValueSource).filter(
                        ValueSource.platform_id == platform.id
                    ).filter(
                        ValueSource.value_id.in_(
                            db.session.query(Value.id).filter(
                                Value.external_object_id == obj.id
                            )
                        )
                    ).delete(
                        synchronize_session=False
                    )

                    # Remove attributes with no sources
                    db.session.query(Value).filter(
                        Value.external_object_id == obj.id
                    ).filter(~Value.sources.any()).delete(synchronize_session=False)

                    db.session.delete(existing)
                    db.session.commit()

            link = (
                db.session.query(ObjectLink)
                .filter(ObjectLink.external_id == external_id)
                .filter(ObjectLink.platform == platform)
                .first()
            )

            if link is None:
                it.write("> LINK {} {} ({})".format(id, external_id, platform.slug))
                obj.links.append(
                    ObjectLink(
                        external_object=obj, platform=platform, external_id=external_id
                    )
                )
            elif link.external_object != obj:
                it.write("> MERGE {} {}".format(id, external_id))

                try:
                    link.external_object.merge_and_delete(obj, db.session)
                except Exception as e:
                    it.write(str(e))
            else:
                it.write(
                    "> ALREADY MERGED {} {} ({})".format(id, external_id, platform.slug)
                )

        db.session.commit()


@click.command("merge-episodes")
@with_appcontext
def merge_episodes():
    """Merge episodes that are in the same series"""
    from sqlalchemy import and_
    from sqlalchemy.orm import aliased
    from .scheme.object import Episode
    from .app import db

    candidates = set()
    other = aliased(Episode)

    query = (
        db.session.query(Episode.external_object_id, other.external_object_id)
        .join(
            (
                other,
                and_(
                    Episode.episode == other.episode,
                    Episode.season == other.season,
                    Episode.series_id == other.series_id,
                    Episode.external_object_id != other.external_object_id,
                ),
            )
        )
        .filter(Episode.episode is not None and Episode.season is not None)
    )

    candidates = frozenset([frozenset([q[0], q[1]]) for q in query])

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
        db.session.query(v1, v2)
        .filter(v1.external_object_id == v2.external_object_id)
        .filter(v1.type == v2.type)
        .filter(v1.text == v2.text)
        .filter(v1.id != v2.id)
    )

    done = set()

    for (v1, v2) in tqdm(values):
        if v1.id in done or v2.id in done:
            continue

        for s2 in v2.sources:
            if not any(s1.platform == s2.platform for s1 in v1.sources):
                v1.sources.append(
                    ValueSource(platform=s2.platform, score_factor=s2.score_factor)
                )
            db.session.delete(s2)
        done.add(v2.id)

        db.session.delete(v2)
        db.session.commit()


@click.command("download-countries")
@with_appcontext
def download_countries():
    """Download the countries definition json"""
    from flask import current_app
    from .countries import update_data

    DATA_FILE = Path(current_app.instance_path).joinpath("countries.json")
    update_data(DATA_FILE)


@click.command("attach-session")
@with_appcontext
@click.option(
    "--platform", "-p", type=PLATFORM, help="Only attach scrap from this platform"
)
@click.option(
    "--type",
    "-t",
    type=EXTERNAL_OBJECT_TYPE,
    help="Only attach scrap that have enough of this external object type",
)
@click.option(
    "--after",
    "-a",
    type=click.DateTime(),
    default="1970-01-01",
    show_default=True,
    help="Attach scraps that ran after this date",
)
@click.option(
    "--before",
    "-b",
    type=click.DateTime(),
    default=str(datetime.now().replace(microsecond=0)),
    show_default="now",
    help="Attach scraps that ran before this date",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=8,
    show_default=True,
    help="How many objects the scrap should have to attach",
)
@click.option(
    "--status",
    "-s",
    type=SCRAP_STATUS,
    multiple=True,
    help="What status the scrap should have to attach",
)
@click.argument("session", type=SESSION)
def attach_session(platform, before, after, session, type, limit, status):
    """Attach scraps to a session"""
    from .app import db
    from .scheme.object import ExternalObject, scrap_link
    from .scheme.platform import Scrap
    from sqlalchemy import func
    from sqlalchemy.exc import InvalidRequestError

    query = db.session.query(Scrap).filter(Scrap.date <= before, Scrap.date >= after)

    if status:
        query = query.filter(Scrap.status.in_(status))

    if platform is not None:
        query = query.filter(Scrap.platform == platform)

    if type is not None:
        query = query.filter(
            db.session.query(func.count(ExternalObject.id))
            .join(ExternalObject.links)
            .join(scrap_link)
            .correlate(Scrap)
            .filter(ExternalObject.type == type)
            .filter(scrap_link.columns.scrap_id == Scrap.id)
            .as_scalar()
            >= limit
        )
    else:
        query = query.filter(
            db.session.query(func.count(ExternalObject.id))
            .join(ExternalObject.links)
            .join(scrap_link)
            .correlate(Scrap)
            .filter(scrap_link.columns.scrap_id == Scrap.id)
            .as_scalar()
            >= limit
        )

    for scrap in query:
        try:
            scrap.sessions.append(session)
            print("Attaching {} to {}".format(scrap, session))
        except InvalidRequestError:
            print("{} is already attached".format(scrap))
        db.session.add(scrap)

    db.session.commit()


@click.command("fix-titles")
@with_appcontext
def fix_titles():
    """Fix countries attributes with no ISO codes"""
    import re
    from .scheme.value import Value, ValueSource
    from .app import db
    from tqdm import tqdm

    values = list(
        db.session.query(Value)
        .filter(Value.text.like("%[%]"))
        .filter(Value.type == ValueType.TITLE)
        .all()
    )

    added = 0

    for v in tqdm(values):
        new = re.sub(r"\[.*\]", "", v.text).strip()

        existing = (
            db.session.query(Value)
            .filter(
                Value.type == ValueType.TITLE,
                Value.text == new,
                Value.external_object_id == v.external_object_id,
            )
            .first()
        )

        if existing is None:
            added += 1
            value = Value(
                type=ValueType.TITLE, text=new, external_object_id=v.external_object_id
            )

            db.session.add(value)

            for source in v.sources:
                value.sources.append(
                    ValueSource(
                        platform=source.platform, score_factor=source.score_factor
                    )
                )

    db.session.commit()
    print("Fixed {} titles out of {}".format(added, len(values)))


@click.command("fix-countries")
@with_appcontext
def fix_countries():
    """Fix countries attributes with no ISO codes"""
    from sqlalchemy.sql.expression import func
    from .scheme.value import Value, ValueSource
    from .app import db
    from .countries import lookup
    from tqdm import tqdm

    values = list(
        db.session.query(Value)
        .filter(
            ~Value.external_object_id.in_(
                db.session.query(Value.external_object_id)
                .filter(Value.type == ValueType.COUNTRY)
                .filter(func.length(Value.text) == 2)
            )
        )
        .filter(Value.type == ValueType.COUNTRY)
        .all()
    )

    added = 0

    for v in tqdm(values):
        new = lookup(v.text)
        if new is not None:
            added += 1

            value = Value(
                type=ValueType.COUNTRY,
                text=new,
                external_object_id=v.external_object_id,
            )

            db.session.add(value)

            for source in v.sources:
                value.sources.append(
                    ValueSource(
                        platform=source.platform, score_factor=source.score_factor
                    )
                )
    db.session.commit()
    print("Fixed {} countries out of {}".format(added, len(values)))


def setup_cli(app):
    app.cli.add_command(attach_session)
    app.cli.add_command(download_countries)
    app.cli.add_command(fix_attributes)
    app.cli.add_command(fix_countries)
    app.cli.add_command(fix_titles)
    app.cli.add_command(import_csv)
    app.cli.add_command(match)
    app.cli.add_command(merge)
    app.cli.add_command(merge_episodes)
    app.cli.add_command(nuke)
    app.cli.add_command(worker)
