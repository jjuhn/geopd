from flask import Blueprint
from sqlalchemy_jsonapi.serializer import JSONAPI

from geopd import app
from geopd.orm import Base

api_blueprint = Blueprint('api', __name__)

jsonapi = JSONAPI(Base)

import users
import cores
import posts

app.register_blueprint(api_blueprint, url_prefix='/api')
