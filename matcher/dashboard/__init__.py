from flask import Blueprint

from . import views

blueprint = Blueprint('dashboard', __name__,
                      template_folder='templates')

blueprint.add_url_rule('/', view_func=views.home.HomeView.as_view('home'))

blueprint.add_url_rule('/scraps', view_func=views.scraps.ScrapListView.as_view('scrap_list'))

blueprint.add_url_rule('/platforms', view_func=views.platforms.PlatformListView.as_view('platform_list'))
blueprint.add_url_rule('/platforms/<slug>', view_func=views.platforms.ShowPlatformView.as_view('show_platform'))

blueprint.add_url_rule('/objects', view_func=views.objects.ObjectListView.as_view('object_list'))
blueprint.add_url_rule('/objects/<int:id>', view_func=views.objects.ShowObjectView.as_view('show_object'))

blueprint.add_url_rule('/exports/factories',
                       view_func=views.exports.ExportFactoryListView.as_view('export_factory_list'))
blueprint.add_url_rule('/exports/factories/<int:id>',
                       view_func=views.exports.ShowExportFactoryView.as_view('show_export_factory'))
blueprint.add_url_rule('/exports/files', view_func=views.exports.ExportFileListView.as_view('export_file_list'))
blueprint.add_url_rule('/exports/files/<int:id>',
                       view_func=views.exports.ShowExportFileView.as_view('show_export_file'))
blueprint.add_url_rule('/exports/files/<int:id>/download',
                       view_func=views.exports.DownloadExportFileView.as_view('download_export_file'))
blueprint.add_url_rule('/exports/files/<int:id>/process',
                       view_func=views.exports.ProcessExportFileView.as_view('process_export_file'))
