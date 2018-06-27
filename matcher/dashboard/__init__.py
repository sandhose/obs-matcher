from flask import Blueprint

from . import views

blueprint = Blueprint('dashboard', __name__)

blueprint.add_url_rule('/', view_func=views.home.HomeView.as_view('home'))
