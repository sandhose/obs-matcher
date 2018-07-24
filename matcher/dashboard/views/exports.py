import gzip

from flask import render_template, send_file
from flask.views import View

from matcher.mixins import DbMixin
from matcher.scheme.export import ExportFile

__all__ = ['ExportFileListView', 'ShowExportFileView']


class ExportFileListView(View, DbMixin):
    def dispatch_request(self):
        query = self.query(ExportFile)

        ctx = {}
        ctx['page'] = query.paginate()

        return render_template('exports/files/list.html', **ctx)


class DownloadExportFileView(View, DbMixin):
    def dispatch_request(self, id):
        export_file = self.query(ExportFile).get_or_404(id)

        response = send_file(export_file.path + ".gz",
                             mimetype="text/csv",
                             as_attachment=True,
                             attachment_filename=export_file.path.split('/')[-1])
        response.headers['Content-Encoding'] = 'gzip'
        return response


class ShowExportFileView(View, DbMixin):
    def dispatch_request(self, id):
        export_file = self.query(ExportFile).get_or_404(id)

        ctx = {}
        ctx['export_file'] = export_file

        return render_template('exports/files/show.html', **ctx)
