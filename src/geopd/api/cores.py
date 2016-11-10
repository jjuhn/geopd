from flask import jsonify
from flask import request
from flask_login import login_required

from can.web.orm import db
from can.web.api import api_blueprint as api
from sa_jsonapi import serializer as jsonapi


@api.route('/cores/')
@login_required
def get_cores():
    response = jsonapi.get_collection(db, request.args, 'cores')
    return jsonify(response.document), response.status


@api.route('/cores/<int:core_id>')
@login_required
def get_core(core_id):
    response = jsonapi.get_resource(db, request.args, 'cores', core_id)
    return jsonify(response.document), response.status


@api.route('/cores/<int:core_id>/posts/')
@login_required
def get_core_posts(core_id):
    response = jsonapi.get_related(db, request.args, 'cores', core_id, 'posts')
    return jsonify(response.document), response.status
