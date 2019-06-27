from pathlib import Path
import json, io, shutil
from matcher.scheme.import_ import ImportFile
from matcher.scheme.platform import Platform, Session
from matcher.scheme.provider import Provider
from matcher.scheme.enums import *
from matcher.app import db
from matcher import app
from matcher.tasks.import_ import process_file

with io.open("/tmp/files.json", "r", encoding="utf-8") as f:
    files = json.load(f)

#  {
#    "id": 130,
#    "filename": "cz_dafilms_movies-20190220-104134 - Copy.tsv",
#    "field": {
#      "country": "attribute_list.country",
#      "director": "attribute_list.name",
#      "duration": "attribute.duration",
#      "platform_id": "",
#      "presence_date": "",
#      "eidr_object_id": "",
#      "imdb_object_id": "",
#      "isan_object_id": "",
#      "original_title": "attribute.title",
#      "production_date": "attribute.date",
#      "platform_object_id": "link.dafilms-cz",
#      "provider_object_id": "link.filmtoro-global",
#      "platform_object_title": "attribute.title"
#    },
#    "imported_external_object_type": "movie",
#    "platform_id": 222,
#    "provider_id": 3,
#    "sessions": [
#      5
#    ]
#  },

app.app_context().push()


for f in files:
    p = Path("/var/cache/scraping/production/imports") / (str(f["id"]) + ".csv")
    if not p.exists():
        print("skipping", f)
        continue

    provider_id = f["provider_id"]
    platform_id = f["platform_id"]
    try:
        provider = db.session.query(Provider).filter(Provider.id == provider_id).one()
        platform = db.session.query(Platform).filter(Platform.id == platform_id).one()
    except:
        print(f"Provider or platform not found, skipping {f}.")
        continue

    new_file = ImportFile(
        filename=f["filename"],
        fields=f["field"],
        imported_external_object_type=ExternalObjectType.from_name(
            f["imported_external_object_type"]
        ),
        platform_id=f["platform_id"],
        status=ImportFileStatus.UPLOADED,
        provider_id=f["provider_id"],
    )

    for s in f["sessions"]:
        ses = db.session.query(Session).get(s)
        if ses is None:
            print("Could not find session", s, f)
            continue
        new_file.sessions.append(ses)

    db.session.add(new_file)
    db.session.commit()

    shutil.copyfile(p, new_file.path)

    t = process_file.apply_async((new_file.id,))

    print(new_file.id, t.task_id)
