from flask import jsonify
from flask import request
from flask_login import login_required

from geopd.core import db
from geopd.core import api
from sa_jsonapi import serializer as jsonapi


@api.route('/users/')
@login_required
def get_users():
    response = jsonapi.get_collection(db.session, request.args, 'users')
    return jsonify(response.document), response.status


@api.route('/users/<int:user_id>')
@login_required
def get_user(user_id):
    response = jsonapi.get_resource(db.session, request.args, 'users', user_id)
    return jsonify(response.document), response.status

@api.route('/users/<int:user_id>/address')
@login_required
def get_user_address(user_id):
    response = jsonapi.get_related(db.session, request.args, 'users', user_id, 'address')
    return jsonify(response.document), response.status

@api.route('/users/<int:user_id>/address', methods=['PATCH'])
@login_required
def update_user_address(user_id):
    response = jsonapi.patch_resource(db.session, request.args, request.get_json(), 'user-addresses', user_id)
    return jsonify(response.document), response.status

@api.route('/permissions/')
def get_permissions():
    response = jsonapi.get_collection(db.session, request.args, 'permissions')
    return jsonify(response.document), response.status

