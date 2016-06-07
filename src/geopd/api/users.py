from flask_login import login_required
from geopd.api import api_blueprint as api
from geopd.jsonapi import get_resource, get_collection
from geopd.orm.model import User


@api.route('/users/')
@login_required
def get_users():
    return get_collection(User.query)


@api.route('/users/<int:id>')
@login_required
def get_user(id):
    return get_resource(User.query.filter(User.id == id))
