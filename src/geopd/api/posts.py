from flask_login import login_required
from geopd.api import api_blueprint as api
from geopd.jsonapi import get_resource, get_collection
from geopd.orm.model import CorePost


@api.route('/posts/')
@login_required
def get_core_posts():
    return get_collection(CorePost.query)


@api.route('/posts/<int:id>')
@login_required
def get_core_post(id):
    return get_resource(CorePost.query.filter(CorePost.id == id))