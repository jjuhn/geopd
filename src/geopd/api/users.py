from flask import request
from flask import jsonify
from flask_login import login_required
from geopd.api import api_blueprint as api
from geopd.api import jsonapi
from geopd.orm import db


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
