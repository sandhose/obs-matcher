import json

from matcher import app
from matcher.app import db
from matcher.scheme.import_ import ImportFile, ImportFileStatus
from sqlalchemy import or_

app.app_context().push()

files = (
    db.session.query(ImportFile)
    .filter(
        or_(
            ImportFile.status == ImportFileStatus.DONE,
            ImportFile.status == ImportFileStatus.PROCESSING,
        )
    )
    .filter(ImportFile.id > 91)
    .all()
)

files = [
    {
        "id": f.id,
        "filename": f.filename,
        "field": f.fields,
        "imported_external_object_type": "movie",
        "platform_id": f.platform.id,
        "provider_id": f.provider.id,
        "sessions": [s.id for s in f.sessions],
    }
    for f in files
]

files = json.dumps(files)

print(files)
