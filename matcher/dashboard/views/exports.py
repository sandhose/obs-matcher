import gzip

from flask import render_template, send_file, request
from flask.views import View

from matcher.mixins import DbMixin
from matcher.scheme.export import ExportFactory, ExportFile, ExportTemplate
from ..forms.exports import ExportFactoryListFilter

__all__ = ['ExportFileListView', 'DownloadExportFileView',
           'ShowExportFileView', 'ExportFactoryListView', 'ShowExportFactoryView']


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
        ctx['file'] = export_file

        return render_template('exports/files/show.html', **ctx)


class ExportFactoryListView(View, DbMixin):
    def dispatch_request(self):
        query = self.query(ExportFactory).join(ExportFactory.template)
        form = ExportFactoryListFilter(request.args)

        if form.validate():
            if form.row_type.data:
                query = query.filter(ExportTemplate.row_type.in_(form.row_type.data))

            if form.iterator.data:
                query = query.filter(ExportFactory.iterator.in_(form.iterator.data))

            if form.external_object_type.data:
                query = query.filter(ExportTemplate.external_object_type.in_(form.external_object_type.data))

        ctx = {}
        ctx['filter_form'] = form
        ctx['page'] = query.paginate()

        return render_template('exports/factories/list.html', **ctx)


class ShowExportFactoryView(View, DbMixin):
    def dispatch_request(self, id):
        export_factory = self.query(ExportFactory).get_or_404(id)

        ctx = {}
        ctx['factory'] = export_factory

        return render_template('exports/factories/show.html', **ctx)
