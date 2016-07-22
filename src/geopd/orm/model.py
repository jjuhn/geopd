"""
Operational database interface.
"""
import os.path

import pkg_resources
from flask import url_for
from inflection import titleize
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.schema import Table
from sqlalchemy.types import Date

from can.web.orm.model import *

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


project_investigator_table = Table('project_investigators', Base.metadata,
                                   Column('project_id', Integer, ForeignKey('projects.id'), primary_key=True),
                                   Column('investigator_id', Integer, ForeignKey('users.id'), primary_key=True))

core_leader_table = Table('core_leaders', Base.metadata,
                          Column('core_id', Integer, ForeignKey('cores.id'), primary_key=True),
                          Column('leader_id', Integer, ForeignKey('users.id'), primary_key=True))

user_response_choice_table = Table('user_response_choices', Base.metadata,
                                   Column('response_id', Integer, ForeignKey('user_responses.id'), primary_key=True),
                                   Column('choice_id', Integer, ForeignKey('survey_question_choices.id'),
                                          primary_key=True))


########################################################################################################################
# Models
########################################################################################################################


class UserBio(Base):
    id = Column(Integer, ForeignKey(User.id), primary_key=True, autoincrement=False)
    research_interests = Column(Text)
    research_experience = Column(Text)

    user = relationship(User, foreign_keys=[id], backref=backref('bio', uselist=False))


class Project(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text, unique=True, nullable=False)

    investigators = relationship(User, secondary=project_investigator_table)

    def __init__(self, name, description, investigators=list()):
        self.name = name
        self.description = description
        self.investigators = investigators


class Publication(Base):
    id = Column(Integer, primary_key=True, autoincrement=False)  # PubMed
    title = Column(Text, nullable=False)
    source = Column(Text, nullable=False)
    issue = Column(Text, nullable=False)
    volume = Column(Text, nullable=False)
    pages = Column(Text, nullable=False)
    authors = Column(Text, nullable=False)
    abstract = Column(Text)
    published_on = Column(Date, nullable=False)
    epublished_on = Column(Date)

    def __init__(self, id, title):
        self.id = id
        self.title = title

    @property
    def pdf_url(self):
        filename = os.path.join('pubmed', '{0}.pdf'.format(self.id))
        fullpath = pkg_resources.resource_filename('geopd', os.path.join('static', filename))
        if os.path.exists(fullpath):
            return url_for('web.static', filename='pubmed/{0}.pdf'.format(self.id))


class Meeting(Base):
    id = Column(Integer, primary_key=True)
    city = Column(Text(convert_unicode=True), nullable=False)
    year = Column(Integer, nullable=False, unique=True)
    carousel = Column(Boolean, nullable=False, default=False, server_default=false())
    program = Column(Boolean, nullable=False, default=False, server_default=false())

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
        return url_for('web.static', filename='images/meetings/{0}.jpg'.format(self.city.lower()))


class Core(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    key = Column(Text, nullable=False, unique=True)
    survey_id = Column(Integer, ForeignKey('surveys.id'))

    leaders = relationship(User, secondary=core_leader_table)
    survey = relationship('Survey')

    def __init__(self, name, key):
        self.name = name
        self.key = key

    @property
    def image_url(self):
        return url_for('web.static', filename='images/cores/{0}.jpg'.format(self.key))


class CorePost(Base):
    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_on = Column(DateTime)
    author_id = Column(Integer, ForeignKey('users.id'))
    core_id = Column(Integer, ForeignKey('cores.id'))

    author = relationship(User, foreign_keys=[author_id], backref=backref('core_posts'))
    core = relationship(Core, foreign_keys=[core_id], backref=backref('posts'))

    def __init__(self, title, body):
        self.title = title
        self.body = body
        self.author = current_user


class CorePostComment(CommentMixin, Base):
    core_post_id = Column(Integer, ForeignKey(CorePost.id), nullable=True)
    core_post = relationship(CorePost, backref=backref('comments'))


class Survey(Base):
    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    description = Column(Text)

    parent_type = Column(Text)
    parent_id = Column(Text)

    def __init__(self, title, description=None):
        self.title = titleize(title)
        self.description = description


class SurveyQuestionType(Base):
    id = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(Text, nullable=False, unique=True)

    def __init__(self, type_id, name):
        self.id = type_id
        self.name = name

    def __str__(self):
        return self.name


class SurveyQuestion(Base):
    __table_args__ = UniqueConstraint('id', 'name'),

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    text = Column(Text, nullable=False)
    order = Column(Integer)

    survey_id = Column(Integer, ForeignKey(Survey.id), nullable=False)
    survey = relationship(Survey, uselist=False,
                          backref=backref('questions',
                                          collection_class=attribute_mapped_collection('name')))

    type_id = Column(Integer, ForeignKey(SurveyQuestionType.id), nullable=False)
    type = relationship(SurveyQuestionType, uselist=False)

    def __init__(self, name, text, type_object, order=None):
        self.name = name
        self.text = text
        self.type = type_object
        self.order = order


class SurveyQuestionChoice(Base):
    __table_args__ = UniqueConstraint('question_id', 'label'),

    id = Column(Integer, primary_key=True)
    label = Column(Text, nullable=False)

    question_id = Column(Integer, ForeignKey(SurveyQuestion.id), nullable=False)
    question = relationship(SurveyQuestion, uselist=False, backref=backref('choices'))

    def __init__(self, label):
        self.label = label


class UserSurvey(Base):
    __table_args__ = UniqueConstraint('user_id', 'survey_id'),

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    survey_id = Column(Integer, ForeignKey(Survey.id), nullable=False)
    completed_on = Column(DateTime)
    updated_on = Column(DateTime)

    user = relationship(User, uselist=False,
                        backref=backref('surveys', collection_class=attribute_mapped_collection('survey_id')))
    survey = relationship(Survey, uselist=False)
    responses = relationship('UserResponse', collection_class=attribute_mapped_collection('name'),
                             backref=backref('user_survey', uselist=False))

    def __init__(self, user, survey):
        self.user = user
        self.survey = survey

    @hybrid_property
    def title(self):
        return self.survey.title


class UserResponse(Base):
    __table_args__ = UniqueConstraint('user_survey_id', 'question_id'),

    id = Column(Integer, primary_key=True)
    user_survey_id = Column(Integer, ForeignKey(UserSurvey.id), nullable=False)
    question_id = Column(Integer, ForeignKey(SurveyQuestion.id), nullable=False)
    question = relationship(SurveyQuestion, uselist=False, lazy='joined')

    @hybrid_property
    def name(self):
        return self.question.name

    def __init__(self, user_survey, question):
        self.question = question
        self.user_survey = user_survey

    answer_text = Column(Text)
    answer_yesno = Column(Boolean)
    answer_choices = relationship(SurveyQuestionChoice, secondary=user_response_choice_table)
