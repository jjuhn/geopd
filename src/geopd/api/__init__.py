from flask import Blueprint

from geopd import app

api_blueprint = Blueprint('api', __name__)
app.register_blueprint(api_blueprint, url_prefix='/api')

import cores
