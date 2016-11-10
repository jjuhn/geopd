from flask import jsonify
from flask import request
from flask_login import login_required

from can.web.orm import db
from can.web.api import api_blueprint as api
from sa_jsonapi import serializer as jsonapi


@api.route('/core-posts/')
@login_required
def get_posts():
    response = jsonapi.get_collection(db, request.args, 'core-posts')
    return jsonify(response.document), response.status


@api.route('/core-posts/<int:post_id>')
@login_required
def get_post(post_id):
    response = jsonapi.get_resource(db, request.args, 'core-posts', post_id)
    return jsonify(response.document), response.status


@api.route('/core-post-comments/')
@login_required
def get_core_post_comments():
    response = jsonapi.get_collection(db, request.args, 'core-post-comments')
    return jsonify(response.document), response.status


@api.route('/core-post-comments/', methods=['POST'])
@login_required
def create_core_post_comment():
    response = jsonapi.post_resource(db, request.args, request.get_json(), 'core-post-comments')
    return jsonify(response.document), response.status


@api.route('/core-post-comments/<int:post_id>', methods=['PATCH'])
@login_required
def update_core_post_comment(post_id):
    response = jsonapi.patch_resource(db, request.args, request.get_json(), 'core-post-comments', post_id)
    return jsonify(response.document), response.status


@api.route('/core-post-comments/<int:post_id>', methods=['DELETE'])
@login_required
def delete_core_post_comment(post_id):
    response = jsonapi.delete_resource(db, 'core-post-comments', post_id)
    return jsonify(response.document), response.status


@api.route('/project-posts/')
@login_required
def get_project_posts():
    response = jsonapi.get_collection(db, request.args, 'project-posts')
    return jsonify(response.document), response.status


@api.route('/project-posts/<int:post_id>')
@login_required
def get_project_post(post_id):
    response = jsonapi.get_collection(db, request.args, 'project-posts', post_id)
    return jsonify(response.document), response.status


@api.route('/project-post-comments/')
@login_required
def get_project_post_comments():
    response = jsonapi.get_collection(db, request.args, 'project-post-comments')
    return jsonify(response.document), response.status


@api.route('/project-post-comments/', methods=['POST'])
@login_required
def create_project_post_comment():
    response = jsonapi.post_resource(db, request.args, request.get_json(), 'project-post-comments')
    return jsonify(response.document), response.status


@api.route('/project-post-comments/<int:post_id>', methods=['PATCH'])
@login_required
def update_project_post_comment(post_id):
    response = jsonapi.patch_resource(db, request.args, request.get_json(), 'project-post-comments', post_id)
    return jsonify(response.document), response.status


@api.route('/project-post-comments/<int:post_id>', methods=['DELETE'])
@login_required
def delete_project_post_comment(post_id):
    response = jsonapi.delete_resource(db, 'project-post-comments', post_id)
    return jsonify(response.document), response.status


@api.route('/communications-posts/')
@login_required
def get_communication_posts():
    response = jsonapi.get_collection(db, request.args, 'com-posts')
    return jsonify(response.document), response.status



@api.route('/communications-posts/<int:post_id>')
@login_required
def get_communication_post(post_id):
    response = jsonapi.get_collection(db, request.args, 'com-posts', post_id)
    return jsonify(response.document), response.status


@api.route('/com-post-comments/')
@login_required
def get_communication_post_comments():
    response = jsonapi.get_collection(db, request.args, 'com-post-comments')
    return jsonify(response.document), response.status


@api.route('/com-post-comments/', methods=['POST'])
@login_required
def create_communication_post_comment():
    response = jsonapi.post_resource(db, request.args, request.get_json(), 'com-post-comments')
    return jsonify(response.document), response.status


@api.route('/com-post-comments/<int:post_id>', methods=['PATCH'])
@login_required
def update_communication_post_comment(post_id):
    response = jsonapi.patch_resource(db, request.args, request.get_json(), 'com-post-comments', post_id)
    return jsonify(response.document), response.status


@api.route('/com-post-comments/<int:post_id>', methods=['DELETE'])
@login_required
def delete_communication_post_comment(post_id):
    response = jsonapi.delete_resource(db, 'communications-post-comments', post_id)
    return jsonify(response.document), response.status

