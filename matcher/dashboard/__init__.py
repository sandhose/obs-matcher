from flask import Blueprint

from . import views

blueprint = Blueprint('dashboard', __name__,
                      template_folder='templates')

blueprint.add_url_rule('/', view_func=views.home.HomeView.as_view('home'))
blueprint.add_url_rule('/scraps', view_func=views.scraps.ScrapListView.as_view('scrap_list'))
blueprint.add_url_rule('/platforms', view_func=views.platforms.PlatformListView.as_view('platform_list'))
blueprint.add_url_rule('/platforms/<slug>', view_func=views.platforms.ShowPlatformView.as_view('show_platform'))
blueprint.add_url_rule('/objects/', view_func=views.objects.ObjectListView.as_view('object_list'))
blueprint.add_url_rule('/objects/<int:id>', view_func=views.objects.ShowObjectView.as_view('show_object'))
