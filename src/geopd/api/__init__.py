from flask import Blueprint

from geopd import app

api_blueprint = Blueprint('api', __name__)

import users
import institutions
import cores

app.register_blueprint(api_blueprint, url_prefix='/api')
