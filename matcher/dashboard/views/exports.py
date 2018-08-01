from typing import Dict, Any, Set  # noqa

from flask import flash, redirect, render_template, request, send_file, url_for
from flask.views import View
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload, undefer

from matcher.mixins import CeleryMixin, DbMixin
from matcher.scheme.enums import PlatformType
from matcher.scheme.export import ExportFactory, ExportFile, ExportTemplate
from matcher.scheme.platform import Platform, PlatformGroup, Session

from ..forms.exports import (ExportFactoryListFilter, ExportFileFilter,
                             NewExportFileForm,)

__all__ = ['ExportIndexView', 'ExportFileListView', 'DownloadExportFileView',
           'NewExportFileView', 'ShowExportFileView', 'ExportFactoryListView',
           'ShowExportFactoryView']


def build_filter_cache(files, session) -> Dict[str, Dict[int, Any]]:
    """Builds a filter cache used by the filter_display jinja filter"""
    filters = {}  # type: Dict[str, Set[str]]
    for file in files:
        for key, value in file.filters.items():
            existing = filters.get(key, set())  # type: Set[str]
            existing.update(k.strip().upper() for k in value.split(','))
            filters[key] = existing

    cache = {}
    if 'platform.id' in filters:
        cache['platform.id'] = dict(session.query(Platform.id, Platform).
                                    filter(Platform.id.in_(int(i) for i in filters['platform.id'])).
                                    all())

    if 'platform.group_id' in filters:
        cache['platform.group_id'] = dict(session.query(PlatformGroup.id, PlatformGroup).
                                          filter(PlatformGroup.id.in_(int(i) for i in filters['platform.group_id'])).
                                          all())

    return cache


class ExportIndexView(View):
    def dispatch_request(self):
        return render_template('exports/index.html')


class ExportFileListView(View, DbMixin):
    def dispatch_request(self):
        form = ExportFileFilter(request.args)
        form.factory.query = self.query(ExportFactory)
        form.template.query = self.query(ExportTemplate)
        form.session.query = self.query(Session)

        query = self.query(ExportFile).join(ExportFile.template).options(undefer(ExportFile.last_activity))

        if form.validate():
            if form.status.data:
                query = query.filter(ExportFile.status.in_(form.status.data))

            if form.row_type.data:
                query = query.filter(ExportTemplate.row_type.in_(form.row_type.data))

            if form.external_object_type.data:
                query = query.filter(ExportTemplate.external_object_type.in_(form.external_object_type.data))

            if form.template.data:
                query = query.filter(ExportFile.export_template_id.in_(t.id for t in form.template.data))

            if form.factory.data:
                query = query.filter(ExportFile.export_factory_id.in_(f.id for f in form.factory.data))

            if form.session.data:
                query = query.filter(ExportFile.session_id.in_(s.id for s in form.session.data))

        ctx = {}
        ctx['page'] = query.paginate()
        ctx['filter_form'] = form
        ctx['export_file_filter_cache'] = build_filter_cache(ctx['page'].items, self.session)

        return render_template('exports/files/list.html', **ctx)


class DownloadExportFileView(View, DbMixin):
    def dispatch_request(self, id):
        export_file = self.query(ExportFile).get_or_404(id)

        # FIXME: not every client supports gzip, we should look at the Accept-Encoding header
        response = send_file(export_file.open(mode='rb'),
                             mimetype="text/csv",
                             as_attachment=True,
                             attachment_filename=export_file.path.split('/')[-1])
        response.headers['Content-Encoding'] = 'gzip'
        return response


class DeleteExportFileView(View, DbMixin):
    def dispatch_request(self, id):
        export_file = self.query(ExportFile).get_or_404(id)
        export_file.delete()
        self.session.add(export_file)
        self.session.commit()
        return redirect(url_for('.show_export_file', id=export_file.id))


class ProcessExportFileView(View, DbMixin, CeleryMixin):
    def dispatch_request(self, id):
        export_file = self.query(ExportFile).get_or_404(id)

        export_file.schedule(celery=self.celery)
        self.session.add(export_file)
        self.session.commit()

        flash('Export started, the file will be available soon')

        return redirect(url_for('.show_export_file', id=export_file.id))


class NewExportFileView(View, DbMixin, CeleryMixin):
    def dispatch_request(self):
        form = NewExportFileForm(request.form)
        form.template.query = self.query(ExportTemplate)
        form.session.query = self.query(Session)
        form.filters.platform_id.query = self.query(Platform)
        form.filters.platform_group_id.query = self.query(PlatformGroup)
        form.filters.platform_country.choices = [
            (v, v) for (v, ) in
            self.query(Platform.country).
            order_by(Platform.country).
            filter(func.char_length(Platform.country) == 2).
            filter(or_(Platform.type == PlatformType.TVOD, Platform.type == PlatformType.SVOD)).
            filter(Platform.ignore_in_exports.is_(False)).
            distinct()
        ]

        if request.method == 'POST' and form.validate():
            file = ExportFile(
                path=form.path.data,
                session=form.session.data,
                template=form.template.data,
                filters=form.filters.render(),
            )
            file.schedule(celery=self.celery)
            self.session.add(file)
            self.session.commit()
            return redirect(url_for('.show_export_file', id=file.id))

        ctx = {}
        ctx['form'] = form

        return render_template('exports/files/new.html', **ctx)


class ShowExportFileView(View, DbMixin):
    def dispatch_request(self, id):
        export_file = self.query(ExportFile).get_or_404(id)

        ctx = {}
        ctx['file'] = export_file
        ctx['export_file_filter_cache'] = build_filter_cache([export_file], self.session)

        return render_template('exports/files/show.html', **ctx)


class ExportFactoryListView(View, DbMixin, CeleryMixin):
    def dispatch_request(self):
        query = self.query(ExportFactory).join(ExportFactory.template)

        if request.method == 'POST':
            if request.form.get('action') == 'run':
                factories = [self.query(ExportFactory).get_or_404(factory_id)
                             for factory_id in request.form.getlist('factories', type=int)]
                session = self.query(Session).get_or_404(request.form.get('session', type=int))

                for factory in factories:
                    self.celery.send_task('matcher.tasks.export.run_factory', (factory.id, session.id))

                flash('Exports were scheduled')

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
        ctx['sessions'] = self.query(Session)

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
