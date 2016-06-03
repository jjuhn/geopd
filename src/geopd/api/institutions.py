from flask_login import login_required
from geopd.api import api_blueprint as api
from geopd.jsonapi import get_resource, get_collection
from geopd.orm.model import User, Institution


@api.route('/institutions/')
@login_required
def get_institutions():
    return get_collection(Institution.query)


@api.route('/institutions/<int:id>')
@login_required
def get_institution(id):
    return get_resource(Institution.query.filter(Institution.id == id))