from flask import Blueprint

from . import views

blueprint = Blueprint('dashboard', __name__,
                      template_folder='templates')

blueprint.add_url_rule('/', view_func=views.home.HomeView.as_view('home'))
blueprint.add_url_rule('/scraps', view_func=views.scraps.ScrapListView.as_view('scrap_list'))
blueprint.add_url_rule('/platforms', view_func=views.platforms.PlatformListView.as_view('platform_list'))
