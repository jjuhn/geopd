from geopd.web import application
from geopd.orm.model import *

import csv
import json
import dateutil.parser
import pkg_resources
import os.path
import Bio.Entrez
from inflection import singularize, underscore, camelize


########################################################################################################################
# Initialize Operational Database
########################################################################################################################


def init_db():

    Base.metadata.drop_all(db.bind)
    Base.metadata.create_all(db.bind)

    db.add(UserStatus(User.STATUS_PENDING, 'Pending'))
    db.add(UserStatus(User.STATUS_ACTIVE, 'Active'))
    db.add(UserStatus(User.STATUS_DISABLED, 'Disabled'))

    users_fn = pkg_resources.resource_filename('geopd.orm', os.path.join('data', 'users.tsv'))
    with open(users_fn, 'rU') as users_stream:
        for row in csv.DictReader(users_stream, delimiter='\t'):
            user = User(row['email'], application.config['DEFAULT_PASSWORD'], row['name'])
            user.status_id = User.STATUS_ACTIVE
            user.confirmed = True
            user.force_password_reset = True
            db.add(user)
        db.flush()

    projects_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'projects.tsv'))
    for row in csv.DictReader(projects_stream, delimiter='\t'):
        project = Project(row['name'], row['description'])
        if row['investigators']:
            for name in row['investigators'].split(','):
                project.investigators.append(User.query.join(UserName).filter(UserName.full == name).one())
        db.add(project)

    publications = dict()
    publications_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'publications.tsv'))
    for row in csv.DictReader(publications_stream, delimiter='\t'):
        publications[row['pubmed']] = None

    Bio.Entrez.email = 'ozabaneh@can.ubc.ca'
    Bio.Entrez.tool = 'geopd.orm.util'
    handle = Bio.Entrez.esummary(db='pubmed', id=','.join(publications.keys()))
    for rec in Bio.Entrez.read(handle):
        publication = Publication(rec['Id'], rec['Title'])
        publication.source = rec['FullJournalName']
        publication.volume = rec['Volume']
        publication.issue = rec['Issue']
        publication.pages = rec['Pages']
        publication.authors = ','.join(rec['AuthorList'])
        publication.published_on = dateutil.parser.parse(rec['PubDate'])
        publication.epublished_on = dateutil.parser.parse(rec['EPubDate']) if rec['EPubDate'] else None
        publications[rec['Id']] = publication
        db.add(publication)

    handle = Bio.Entrez.efetch(db='pubmed', id=','.join(publications.keys()), rettype='abstract', retmode='xml')
    for rec in Bio.Entrez.read(handle):
        abstract_lines = []
        if 'Abstract' in rec['MedlineCitation']['Article']:
            for s in rec['MedlineCitation']['Article']['Abstract']['AbstractText']:
                abstract_lines.append(s)
            publications[rec['MedlineCitation']['PMID']].abstract = '\n'.join(abstract_lines)

    db.add(Meeting('Paris', 2005, carousel=True))
    db.add(Meeting('Santorini', 2006, carousel=True))
    db.add(Meeting('Trondheim', 2008, carousel=True))
    db.add(Meeting('Tubingen', 2009, carousel=True))
    db.add(Meeting('Toronto', 2010, carousel=True))
    db.add(Meeting('Evanston', 2011, program=True, carousel=True))
    db.add(Meeting('Seoul', 2012, program=True, carousel=True))
    db.add(Meeting('Luebeck', 2013, program=True, carousel=True))
    db.add(Meeting('Vancouver', 2014, program=True, carousel=True))
    db.add(Meeting('Tokyo', 2015, program=True, carousel=True))
    db.add(Meeting('Luxembourg', 2016, program=True))

    cores_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'cores.tsv'))
    for row in csv.DictReader(cores_stream, delimiter='\t'):
        core = Core(row['name'], key=row['key'])
        if row['leaders']:
            for name in row['leaders'].split(','):
                core.leaders.append(User.query.join(UserName).filter(UserName.full == name).one())
        db.add(core)
    db.flush()

    # survey question types
    question_types = dict()
    question_types['text'] = SurveyQuestionType(QUESTION_TYPE_TEXT, 'text')
    question_types['yesno'] = SurveyQuestionType(QUESTION_TYPE_YESNO, 'yesno')
    question_types['yesno-explain'] = SurveyQuestionType(QUESTION_TYPE_YESNO_EXPLAIN, 'yesno-explain')
    question_types['choices'] = SurveyQuestionType(QUESTION_TYPE_CHOICES, 'choices')

    # import surveys
    surveys_stream = pkg_resources.resource_stream('geopd.orm', os.path.join('data', 'surveys.json'))
    for data in json.load(surveys_stream)['data']:
        survey = Survey(data['title'], data.get('description'))
        survey.init_user_surveys()

        if 'parent' in data:
            models = dict([(c.__name__, c) for c in Base.__subclasses__()])
            resource_type = data['parent']['type']
            resource_id = data['parent']['id']
            model_name = camelize(singularize(underscore(resource_type)))
            if model_name in models.keys():
                parent = models[model_name].query.get(resource_id)
                parent.survey = survey
                survey.parent_type = resource_type
                survey.parent_id = resource_id

        for order, row in enumerate(data['questions'], start=1):
            if row['type'] in question_types.keys():
                attrs = row['attributes']
                question = SurveyQuestion(attrs['name'], attrs['text'], question_types[row['type']], order)
                survey.questions[attrs['name']] = question
                if row['type'] == 'choices' and 'choices' in attrs:
                    for choice in attrs['choices']:
                        question.choices.append(SurveyQuestionChoice(choice))

    db.commit()

