from collections import OrderedDict

from flask import flash, redirect, render_template, request, url_for
from flask.views import View
from sqlalchemy.orm import undefer
from sqlalchemy.orm.attributes import flag_modified

from matcher.mixins import CeleryMixin, DbMixin
from matcher.scheme.enums import ImportFileStatus
from matcher.scheme.import_ import ImportFile
from matcher.scheme.platform import Platform, Session
from matcher.utils import apply_ordering, parse_ordering

from ..forms.imports import EditImport, UploadImport

__all__ = ["ImportFileListView", "ShowImportFileView"]


class ImportFileListView(View, DbMixin):
    def dispatch_request(self):
        form = UploadImport()

        if form.validate_on_submit():
            f = form.file.data
            assert (
                f.filename.split(".")[-1].lower() == "csv"
                or f.content_type == "text/csv"
            )

            file = ImportFile()

            last_import = (
                self.session.query(ImportFile)
                .order_by(ImportFile.last_activity.desc())
                .first()
            )

            # Set those attributes from the latest imported file, defaulting to the column default
            for attr in ["imported_external_object_type", "platform_id", "fields"]:
                setattr(
                    file, attr, getattr(last_import, attr, getattr(file, attr, None))
                )

            file.upload(file=f)
            self.session.add(file)
            self.session.commit()

            f.save(str(file.path))
            return redirect(url_for(".show_import_file", id=file.id))

        query = self.query(ImportFile).options(undefer(ImportFile.last_activity))

        ordering_key, ordering_direction = parse_ordering(
            request.args.get("ordering", None, str)
        )
        query = apply_ordering(
            {
                "date": ImportFile.last_activity,
                "filename": ImportFile.filename,
                None: ImportFile.id,
            },
            query,
            key=ordering_key,
            direction=ordering_direction,
        )

        ctx = {}
        ctx["ordering"] = request.args.get("ordering", None, str)
        ctx["page"] = query.paginate()
        ctx["upload_form"] = form

        return render_template("imports/list.html", **ctx)


class ShowImportFileView(View, DbMixin, CeleryMixin):
    def dispatch_request(self, id):
        file = self.query(ImportFile).get_or_404(id)
        header = file.header()

        file.fields = OrderedDict((key, file.fields.get(key, "")) for key in header)

        formdata = request.form if request.method == "POST" else None
        form = EditImport(formdata, obj=file)
        form.platform.query = self.query(Platform)
        form.sessions.query = self.query(Session)

        platform_choices = self.query(Platform.slug, Platform.name).all()
        for subform in form.fields.entries:
            subform.arg_platform.choices = platform_choices

        if form.validate_on_submit():
            if file.status != ImportFileStatus.UPLOADED:
                flash("Can't edit processed file")
            else:
                form.populate_obj(file)
                flag_modified(file, "fields")
                self.session.add(file)
                self.session.commit()

                if form.save_and_import.data:
                    self.celery.send_task(
                        "matcher.tasks.import_.process_file", [file.id]
                    )
                    flash("Processing started")

        ctx = {}
        ctx["file"] = file
        ctx["form"] = form
        return render_template("imports/show.html", **ctx)
