"""
Operational database interface.
"""
import os.path

import pkg_resources
from flask import url_for

from geopd.core.orm.model import *

########################################################################################################################
# Constants
########################################################################################################################
QUESTION_TYPE_TEXT = 1
QUESTION_TYPE_YESNO = 2
QUESTION_TYPE_YESNO_EXPLAIN = 3
QUESTION_TYPE_CHOICES = 4

########################################################################################################################
# Tables
########################################################################################################################


core_leader_table = db.Table('core_leaders',
                          db.Column('core_id', db.Integer, db.ForeignKey('cores.id'), primary_key=True),
                          db.Column('leader_id', db.Integer, db.ForeignKey('users.id'), primary_key=True))

user_response_choice_table = db.Table('user_response_choices',
                                   db.Column('response_id', db.Integer, db.ForeignKey('user_responses.id'), primary_key=True),
                                   db.Column('choice_id', db.Integer, db.ForeignKey('survey_question_choices.id'),
                                          primary_key=True))

compost_affiliation_table = db.Table('com_posts_affiliations',
                                     db.Column('com_post_id', db.Integer, db.ForeignKey('com_posts.id'), primary_key=True),
                                     db.Column('affiliation_id', db.Integer, db.ForeignKey('affiliations.id'), primary_key=True))


########################################################################################################################
# Models
########################################################################################################################


@User.setup
def _user_setup(user):
    user.bio = UserBio()
    for survey in Survey.query:
        user.surveys[survey.id] = UserSurvey(user, survey)


@enum.unique
class PERMISSION(enum.IntEnum):
    MANAGE_USER_ACCOUNT = Permission.MANAGE_USER_ACCOUNT


class UserBio(db.Model):
    id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True, autoincrement=False)
    research_interests = db.Column(db.Text)
    research_experience = db.Column(db.Text)

    user = db.relationship(User, foreign_keys=[id], backref=db.backref('bio', uselist=False))


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)
    summary = db.Column(db.Text, unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)

    members = db.relationship(User, secondary=lambda:ProjectMember.__table__, backref=db.backref('mprojects'), lazy="dynamic")

    def __init__(self, name, summary, description, investigators=list()):
        self.name = name
        self.summary = summary
        self.description = description
        self.investigators = investigators


class ProjectMember(db.Model):
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id), primary_key=True, autoincrement=False)
    member_id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True, autoincrement=False)
    investigator = db.Column(db.Boolean, default=False)

    def __init__(self, project_id, user_id, investigator):
        self.project_id = project_id
        self.member_id = user_id
        self.investigator = investigator


class ProjectPost(db.Model):
    id = db.Column(db.Integer, primary_key=True,)
    title = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_on = db.Column(db.DateTime)
    author_id = db.Column(db.Integer, db.ForeignKey(User.id))
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id))
    deleted = db.Column(db.Boolean, nullable=False)

    author = db.relationship(User, foreign_keys=[author_id], backref=db.backref('project_posts'))
    project = db.relationship(Project, foreign_keys=[project_id], backref=db.backref('posts'))

    def __init__(self, title, body):
        self.title = title
        self.body = body
        self.author = current_user
        self.deleted = False


class ComPost(db.Model):
    id = db.Column(db.Integer, primary_key=True,)
    title = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_on = db.Column(db.DateTime)
    author_id = db.Column(db.Integer, db.ForeignKey(User.id))

    author = db.relationship(User, foreign_keys=[author_id], backref=db.backref('com_posts'))
    affiliations = db.relationship(lambda:Affiliation, secondary=compost_affiliation_table)

    def __init__(self, title, body):
        self.title = title
        self.body = body
        self.author = current_user


class ComPostComment(CommentMixin, db.Model):
    com_post_id = db.Column(db.Integer, db.ForeignKey(ComPost.id), nullable=True)
    com_post = db.relationship(ComPost, backref=db.backref('comments'))


class ProjectPostComment(CommentMixin, db.Model):
    project_post_id = db.Column(db.Integer, db.ForeignKey(ProjectPost.id), nullable=True)
    project_post = db.relationship(ProjectPost, backref=db.backref('comments'))


class Affiliation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True)
    hidden = db.Column(db.Boolean, nullable=False)
    # posts = db.relationship(ComPost, secondary=compost_affiliation_table)


class Publication(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)  # PubMed
    title = db.Column(db.Text, nullable=False)
    source = db.Column(db.Text, nullable=False)
    issue = db.Column(db.Text, nullable=False)
    volume = db.Column(db.Text, nullable=False)
    pages = db.Column(db.Text, nullable=False)
    authors = db.Column(db.Text, nullable=False)
    abstract = db.Column(db.Text)
    published_on = db.Column(db.Date, nullable=False)
    epublished_on = db.Column(db.Date)

    def __init__(self, id, title):
        self.id = id
        self.title = title

    @property
    def pdf_url(self):
        filename = os.path.join('pubmed', '{0}.pdf'.format(self.id))
        fullpath = pkg_resources.resource_filename('geopd', os.path.join('static', filename))
        if os.path.exists(fullpath):
            return url_for('static', filename='pubmed/{0}.pdf'.format(self.id))


class Meeting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    city = db.Column(db.Text(convert_unicode=True), nullable=False)
    year = db.Column(db.Integer, nullable=False, unique=True)
    carousel = db.Column(db.Boolean, nullable=False, default=False, server_default=false())
    program = db.Column(db.Boolean, nullable=False, default=False, server_default=false())

    def __init__(self, city, year, carousel=None, program=None):
        self.city = city
        self.year = year
        self.carousel = carousel
        self.program = program

    @property
    def title(self):
        return "{0} {1}".format(self.city, self.year)

    @property
    def key(self):
        return self.title.lower().replace(' ', '_')

    @property
    def image_url(self):
        return url_for('static', filename='images/meetings/{0}.jpg'.format(self.city.lower()))


class Core(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False, unique=True)
    key = db.Column(db.Text, nullable=False, unique=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('surveys.id'))

    leaders = db.relationship(User, secondary=core_leader_table)
    survey = db.relationship('Survey')

    def __init__(self, name, key):
        self.name = name
        self.key = key

    @property
    def image_url(self):
        return url_for('static', filename='images/cores/{0}.jpg'.format(self.key))


class CorePost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_on = db.Column(db.DateTime)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    core_id = db.Column(db.Integer, db.ForeignKey('cores.id'))

    author = db.relationship(User, foreign_keys=[author_id], backref=db.backref('core_posts'))
    core = db.relationship(Core, foreign_keys=[core_id], backref=db.backref('posts'))

    def __init__(self, title, body):
        self.title = title
        self.body = body
        self.author = current_user


class CorePostComment(CommentMixin, db.Model):
    core_post_id = db.Column(db.Integer, db.ForeignKey(CorePost.id), nullable=True)
    core_post = db.relationship(CorePost, backref=db.backref('comments'))


class Survey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)

    parent_type = db.Column(db.Text)
    parent_id = db.Column(db.Text)

    def __init__(self, title, description=None):
        self.title = inflection.titleize(title)
        self.description = description

    def init_user_surveys(self):
        for user in User.query:
            user.surveys[self.id] = UserSurvey(user, self)


class SurveyQuestionType(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    name = db.Column(db.Text, nullable=False, unique=True)

    def __init__(self, type_id, name):
        self.id = type_id
        self.name = name

    def __str__(self):
        return self.name


class SurveyQuestion(db.Model):
    __table_args__ = db.UniqueConstraint('id', 'name'),

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    text = db.Column(db.Text, nullable=False)
    order = db.Column(db.Integer)

    survey_id = db.Column(db.Integer, db.ForeignKey(Survey.id), nullable=False)
    survey = db.relationship(Survey, uselist=False,
                          backref=db.backref('questions',
                                          collection_class=attribute_mapped_collection('name')))

    type_id = db.Column(db.Integer, db.ForeignKey(SurveyQuestionType.id), nullable=False)
    type = db.relationship(SurveyQuestionType, uselist=False)

    def __init__(self, name, text, type_object, order=None):
        self.name = name
        self.text = text
        self.type = type_object
        self.order = order


class SurveyQuestionChoice(db.Model):
    __table_args__ = db.UniqueConstraint('question_id', 'label'),

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.Text, nullable=False)

    question_id = db.Column(db.Integer, db.ForeignKey(SurveyQuestion.id), nullable=False)
    question = db.relationship(SurveyQuestion, uselist=False, backref=db.backref('choices'))

    def __init__(self, label):
        self.label = label


class UserSurvey(db.Model):
    __table_args__ = db.UniqueConstraint('user_id', 'survey_id'),

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)
    survey_id = db.Column(db.Integer, db.ForeignKey(Survey.id), nullable=False)
    completed_on = db.Column(db.DateTime)
    updated_on = db.Column(db.DateTime)

    user = db.relationship(User, uselist=False,
                        backref=db.backref('surveys', collection_class=attribute_mapped_collection('survey_id')))
    survey = db.relationship(Survey, uselist=False, backref=db.backref('user_surveys'))
    responses = db.relationship('UserResponse', collection_class=attribute_mapped_collection('name'),
                             backref=db.backref('user_survey', uselist=False))

    def __init__(self, user, survey):
        self.user = user
        self.survey = survey

    @hybrid_property
    def title(self):
        return self.survey.title


class UserResponse(db.Model):
    __table_args__ = db.UniqueConstraint('user_survey_id', 'question_id'),

    id = db.Column(db.Integer, primary_key=True)
    user_survey_id = db.Column(db.Integer, db.ForeignKey(UserSurvey.id), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey(SurveyQuestion.id), nullable=False)
    question = db.relationship(SurveyQuestion, uselist=False, lazy='joined', backref=db.backref('responses'))

    answer_text = db.Column(db.Text)
    answer_yesno = db.Column(db.Boolean)
    answer_choices = db.relationship(SurveyQuestionChoice, secondary=user_response_choice_table)

    @hybrid_property
    def name(self):
        return self.question.name

    def __init__(self, user_survey, question):
        self.question = question
        self.user_survey = user_survey


class UserReferrer(db.Model):
    id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True, autoincrement=False)
    referrer_id = db.Column(db.Integer, db.ForeignKey(User.id))

    referee = db.relationship(User, foreign_keys=[id], backref=db.backref('user_referee', lazy='joined', uselist=False))

    referrer = db.relationship(User, foreign_keys=[referrer_id],
                                 backref=db.backref('userreferrer', lazy='joined'))

    def __init__(self, referee, referrer):
        self.id = referee.id
        self.referrer_id = referrer.id


class CategoryType(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    name = db.Column(db.Text, nullable=False)


class ProjectCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text)
    order = db.Column(db.Integer)
    project_id = db.Column(db.Integer, db.ForeignKey(Project.id))
    type_id = db.Column(db.Integer, db.ForeignKey(CategoryType.id))

    project = db.relationship(Project, foreign_keys=[project_id], backref=db.backref('categories', lazy='joined', order_by=order))
    type = db.relationship(CategoryType, foreign_keys=[type_id], backref=db.backref('categories', lazy='joined'))

from geopd.core import app
import markdown
from flask import Markup

class ContentFile(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    saved_path = db.Column(db.Text, nullable=False)
    file_name = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey(ProjectCategory.id))
    read_and_show = db.Column(db.Boolean)
    display_name = db.Column(db.Text, nullable=False)
    extension = db.Column(db.Text, nullable=False)

    project_category = db.relationship(ProjectCategory, foreign_keys=[category_id], backref=db.backref('content_files'), lazy='joined')


    def __init__(self, file_name, category_id, read_and_show, display_name, extension):
        self.file_name = file_name
        self.category_id = category_id
        self.read_and_show = read_and_show
        self.display_name = display_name
        self.extension = extension


    @hybrid_property
    def read_file(self):
        if self.read_and_show:
            full_path = os.path.join(app.config["PRIVATE_DIR"], self.file_url)
            if os.path.exists(full_path):
                with open(full_path, 'r') as f:
                    read_contents = Markup(markdown.markdown(f.read()))
                    return read_contents

    @property
    def file_url(self):
        filename = os.path.join("projects",
                                str(self.project_category.project.id),
                                str(self.project_category.name.lower().replace(" ", "_")),
                                str(self.file_name))

        return filename


class ContentPublication(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.Text, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey(ProjectCategory.id))
    pmid = db.Column(db.Integer)
    title = db.Column(db.Text, nullable=False)
    source = db.Column(db.Text)
    issue = db.Column(db.Text)
    volume = db.Column(db.Text)
    pages = db.Column(db.Text)
    authors = db.Column(db.Text)
    abstract = db.Column(db.Text)
    published_on = db.Column(db.Date)
    epublished_on = db.Column(db.Date)

    project_category = db.relationship(ProjectCategory,
                                       foreign_keys=[category_id],
                                       backref=db.backref('content_publications'), lazy='joined')

    def __init__(self, title):
        self.title = title

    @property
    def file_url(self):
        filename = os.path.join("projects",
                                str(self.project_category.project.id),
                                str(self.project_category.name.lower().replace(" ", "_")),
                                str(self.file_name))

        return filename


class ContentPedigree(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_name = db.Column(db.Text, nullable=False)
    region = db.Column(db.Text, nullable=False)
    country_code = db.Column(db.Text, nullable=False)
    display_name = db.Column(db.Text, nullable=False)
    pedigree_type = db.Column(db.Text, nullable=False)
    country = db.Column(db.Text, nullable=False)

    category_id = db.Column(db.Integer, db.ForeignKey(ProjectCategory.id))

    project_category = db.relationship(ProjectCategory,
                                       foreign_keys=[category_id],
                                       backref=db.backref('content_pedigrees'), lazy='joined')

    def __init__(self, file_name):
        self.file_name = file_name



