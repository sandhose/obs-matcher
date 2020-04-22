import io
import json
import os
import shutil
from os.path import join
from pathlib import Path

from matcher import app
from matcher.app import db
from matcher.scheme.enums import *
from matcher.scheme.import_ import ImportFile
from matcher.scheme.platform import Platform, Session
from matcher.scheme.provider import Provider
from matcher.tasks.import_ import process_file

app.app_context().push()

# Hard coded session id, you should look up the value in db first
session_id = 1  # FIXME X is 2020 session for series

# Files to be imported. Path should be `provider_id/platform_slug`
source_directory = "/tmp/importme/"
root, import_directories, _ = next(os.walk(source_directory))
for provider_slug in import_directories:
    try:
        provider = (
            db.session.query(Provider).filter(Provider.slug == provider_slug).one()
        )
    except:
        print(f"Failed to find provider {provider_slug} in database. Skipping.")
        continue
    print(f"Importing files for {provider_slug} (id {provider.id}).")

    global_platform = next(
        filter(lambda p: p.type == PlatformType.GLOBAL, provider.platforms), None
    )
    if global_platform is not None:
        print(f"Global platform for {provider_slug} is {global_platform.slug}.")
    else:
        print(f"No global platform defined for {provider_slug}")

    platforms = os.listdir(join(root, provider_slug))
    for platform in platforms:
        filename = platform
        platform_slug, _ = os.path.splitext(filename)
        try:
            platform = (
                db.session.query(Platform).filter(Platform.slug == platform_slug).one()
            )
        except:
            print(f"Failed to find platform {platform_slug} in database. Skipping.")
            continue
        print(f"* {platform_slug} (id {platform.id})")
        # fields = f'"country": "attribute_list.country", "director": "attribute_list.name", "duration": "attribute.duration", "platform_id": "", "presence_date": "", "eidr_object_id": "link.eidr", "imdb_object_id": "link.imdb", "isan_object_id": "link.isan", "original_title": "attribute.title", "production_date": "attribute.date", "platform_object_id": "link.{platform_slug}", "provider_object_id": "link.{provider_slug}", "platform_object_title": "attribute.title"'
        fields = {}
        fields["platform_id"] = ""
        fields["platform_object_id"] = f"link.{platform_slug}"
        fields["imdb_object_id"] = "link.imdb"
        fields["eidr_object_id"] = "link.eidr"
        fields["isan_object_id"] = "link.isan"
        fields["platform_object_title"] = "attribute.title"
        fields["original_title"] = "attribute.title"
        fields["country"] = "attribute_list.country"
        fields["original_release_year"] = "attribute.date"
        fields["genre"] = ""
        fields["creator"] = "attribute_list.name"
        fields["producer"] = ""
        fields["distributor"] = ""
        fields["episode_count"] = ""
        fields["season_count"] = ""
        fields["presence_date"] = ""
        #fields["provider_object_id"] = (
        #    f"link.{global_platform.slug}" if global_platform is not None else ""
        #)
        new_file = ImportFile(
            filename=filename,
            fields=fields,
            imported_external_object_type=ExternalObjectType.from_name("series"),
            platform_id=platform.id,
            status=ImportFileStatus.UPLOADED,
            provider_id=provider.id,
        )

        ses = db.session.query(Session).get(session_id)
        if ses is None:
            print("Could not find session", session_id, platform_slug)
            continue
        new_file.sessions.append(ses)

        db.session.add(new_file)
        db.session.commit()

        old_path = os.path.join(root, provider_slug, filename)
        # Debug info: print(f"Copying from {old_path} to {new_file.path}.")
        shutil.copyfile(old_path, new_file.path)

        t = process_file.apply_async((new_file.id,))

        print(new_file.id, t.task_id)
