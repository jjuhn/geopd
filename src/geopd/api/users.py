from flask import jsonify
from flask import request
from flask_login import login_required

from can.web.orm import db
from can.web.api import api_blueprint as api
from can.web.api import jsonapi


@api.route('/users/')
@login_required
def get_users():
    response = jsonapi.get_collection(db, request.args, 'users')
    return jsonify(response.data), response.status_code


@api.route('/users/<int:user_id>')
@login_required
def get_user(user_id):
    response = jsonapi.get_resource(db, request.args, 'users', user_id)
    return jsonify(response.data), response.status_code


@api.route('/users/<int:user_id>/address')
@login_required
def get_user_address(user_id):
    response = jsonapi.get_related(db, request.args, 'users', user_id, 'address')
    return jsonify(response.data), response.status_code


@api.route('/users/<int:user_id>/address', methods=['PATCH'])
@login_required
def update_user_address(user_id):
    response = jsonapi.patch_resource(db, request.args, request.get_json(), 'user-addresses', user_id)
    return jsonify(response.data), response.status_code

