from flask import jsonify
from flask import request
from flask_login import login_required

from can.web.orm import db
from can.web.api import api_blueprint as api
from can.web.api import jsonapi


@api.route('/surveys/')
@login_required
def get_surveys():
    response = jsonapi.get_collection(db, request.args, 'surveys')
    return jsonify(response.data), response.status_code


@api.route('/surveys/<int:survey_id>')
@login_required
def get_survey(survey_id):
    response = jsonapi.get_resource(db, request.args, 'surveys', survey_id)
    return jsonify(response.data), response.status_code


# @api.route('/surveys/<int:survey_id>/questions')
# @login_required
# def get_survey_questions(survey_id):
#     response = jsonapi.get_related(db, request.args, 'surveys', survey_id, 'questions')
#     return jsonify(response.data), response.status_code


@api.route('/survey-questions/')
@login_required
def get_survey_questions():
    response = jsonapi.get_collection(db, request.args, 'survey-questions')
    return jsonify(response.data), response.status_code


@api.route('/survey-questions/<question_id>')
@login_required
def get_survey_question(question_id):
    response = jsonapi.get_resource(db, request.args, 'survey-questions', question_id)
    return jsonify(response.data), response.status_code
