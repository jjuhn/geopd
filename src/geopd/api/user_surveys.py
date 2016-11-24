from flask import jsonify
from flask_login import login_required

from geopd.core import db
from geopd.core import api
from sa_jsonapi import serializer as jsonapi
from geopd.orm.model import *


@api.route('/user-surveys/')
@login_required
def get_user_surveys():
    response = jsonapi.get_collection(db.session, request.args, 'user-surveys')
    return jsonify(response.document), response.status


@api.route('/user-surveys/<int:user_survey_id>')
@login_required
def get_user_survey(user_survey_id):
    response = jsonapi.get_resource(db.session, request.args, 'user-surveys', user_survey_id)
    return jsonify(response.document), response.status


@api.route('/user-surveys/<int:user_survey_id>/radio-fields')
@login_required
def get_user_survey_radio_fields(user_survey_id):
    response = jsonapi.get_related(db.session, request.args, 'user-surveys', user_survey_id, 'radio-fields')
    return jsonify(response.document), response.status


@api.route('/user-surveys/<int:user_survey_id>/checkbox-choices')
@login_required
def get_user_survey_checkbox_choices(user_survey_id):
    response = jsonapi.get_related(db.session, request.args, 'user-surveys', user_survey_id, 'checkbox-choices')
    return jsonify(response.document), response.status

