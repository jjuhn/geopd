from flask import jsonify
from flask import request
from flask_login import login_required

from can.web.orm import db
from can.web.api import api_blueprint as api
from can.web.api import jsonapi


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


@api.route('/core-post-comments/')
@login_required
def get_core_post_comments():
    response = jsonapi.get_collection(db, request.args, 'core-post-comments')
    return jsonify(response.data), response.status_code


@api.route('/core-post-comments/', methods=['POST'])
@login_required
def create_core_post_comment():
    response = jsonapi.post_collection(db, request.args, request.get_json(), 'core-post-comments')
    return jsonify(response.data), response.status_code


@api.route('/core-post-comments/<int:post_id>', methods=['PATCH'])
@login_required
def update_core_post_comment(post_id):
    response = jsonapi.patch_resource(db, request.args, request.get_json(), 'core-post-comments', post_id)
    return jsonify(response.data), response.status_code


@api.route('/core-post-comments/<int:post_id>', methods=['DELETE'])
@login_required
def delete_core_post_comment(post_id):
    response = jsonapi.delete_resource(db, request.get_json(), 'core-post-comments', post_id)
    return jsonify(response.data), response.status_code
