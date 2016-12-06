from flask import jsonify
from flask import request
from flask_login import login_required

from geopd.core import db
from geopd.core import api
from sa_jsonapi import serializer as jsonapi


@api.route('/projects/')
@login_required
def get_projects():
    response = jsonapi.get_collection(db.session, request.args, 'projects')
    return jsonify(response.document), response.status


@api.route('/projects/<int:project_id>')
@login_required
def get_project(project_id):
    response = jsonapi.get_related(db.session, request.args, 'projects', project_id, 'members')
    return jsonify(response.document), response.status


@api.route('/categories')
@login_required
def get_categories():
    response = jsonapi.get_collection(db.session, request.args, 'project-categories')
    return jsonify(response.document), response.status


@api.route('/project-categories/<int:project_id>')
@login_required
def get_project_categories(project_id):
    response = jsonapi.get_related(db.session, request.args, 'project-categories', project_id, 'project')
    return jsonify(response.document), response.status


@api.route('/content_files')
@login_required
def get_content_files():
    response = jsonapi.get_collection(db.session, request.args, 'content-files')
    return jsonify(response.document), response.status


@api.route('/content_publications')
@login_required
def get_content_publications():
    response = jsonapi.get_collection(db.session, request.args, 'content-publications')
    return jsonify(response.document), response.status


@api.route('/content_pedigrees')
@login_required
def get_content_pedigrees():
    response = jsonapi.get_collection(db.session, request.args, 'content-pedigrees')
    return jsonify(response.document), response.status
