from flask import jsonify
from flask import request
from flask_login import login_required

from can.web.api import api_blueprint as api
from can.web.api import jsonapi
from can.web.orm import db


@api.route('/core-posts/')
@login_required
def get_posts():
    response = jsonapi.get_collection(db, request.args, 'core-posts')
    return jsonify(response.data)


@api.route('/core-posts/<int:post_id>')
@login_required
def get_post(post_id):
    response = jsonapi.get_resource(db, request.args, 'core-posts', post_id)
    return jsonify(response.data)
