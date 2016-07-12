from flask import jsonify
from flask import request
from flask_login import login_required

from can.web.api import api_blueprint as api
from can.web.api import jsonapi
from can.web.orm import db


@api.route('/users/')
@login_required
def get_users():
    response = jsonapi.get_collection(db, request.args, 'users')
    return jsonify(response.data)


@api.route('/users/<int:user_id>')
@login_required
def get_user(user_id):
    response = jsonapi.get_resource(db, request.args, 'users', user_id)
    return jsonify(response.data)
