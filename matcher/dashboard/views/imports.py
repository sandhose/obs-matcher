from flask import render_template
from flask.views import View
from sqlalchemy.orm import undefer

from matcher.mixins import DbMixin
from matcher.scheme.import_ import ImportFile

from ..forms.imports import UploadImport

__all__ = ['ImportFileListView']


class ImportFileListView(View, DbMixin):
    def dispatch_request(self):
        form = UploadImport()

        if form.validate_on_submit():
            f = form.file.data
            assert f.filename.split('.')[-1].lower() == 'csv' or f.content_type == 'text/csv'

            file = ImportFile()
            file.upload(file=f)
            self.session.add(file)
            self.session.commit()

            f.save(str(file.path))

        query = self.query(ImportFile)\
            .options(undefer(ImportFile.last_activity))\
            .order_by(ImportFile.id)

        ctx = {}
        ctx['page'] = query.paginate()
        ctx['upload_form'] = form

        return render_template('imports/list.html', **ctx)


class ShowImportFileView(View, DbMixin):
    def dispatch_request(self, id):
        file = self.query(ImportFile).get_or_404(id)
        ctx = {}
        ctx['file'] = file
        return render_template('imports/show.html', **ctx)
