from flask import redirect, render_template, request, send_file, url_for
from flask.views import View
from sqlalchemy.orm import joinedload

from matcher.mixins import DbMixin, CeleryMixin
from matcher.scheme.enums import ExportFileStatus
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


class ProcessExportFileView(View, DbMixin, CeleryMixin):
    def dispatch_request(self, id):
        export_file = self.query(ExportFile).get_or_404(id)

        export_file.change_status(ExportFileStatus.SCHEDULED)
        self.session.add(export_file)
        self.session.commit()

        self.celery.send_task('matcher.tasks.export.process_file', [export_file.id])

        return redirect(url_for('.show_export_file', id=export_file.id))


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
        export_factory = self.query(ExportFactory)\
            .options(joinedload(ExportFactory.files).joinedload(ExportFile.session),
                     joinedload(ExportFactory.files).undefer(ExportFile.last_activity))\
            .get_or_404(id)

        ctx = {}
        ctx['factory'] = export_factory

        return render_template('exports/factories/show.html', **ctx)
