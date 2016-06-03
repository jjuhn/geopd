from flask_login import login_required
from geopd.api import api_blueprint as api
from geopd.jsonapi import get_resource, get_collection
from geopd.orm.model import Core


@api.route('/cores/')
@login_required
def get_cores():
    return get_collection(Core.query)


@api.route('/cores/<int:id>')
@login_required
def get_core(id):
    return get_resource(Core.query.filter(Core.id == id))