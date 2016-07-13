"""
Operational database interface.
"""
import os.path

import pkg_resources
from flask import url_for
from sqlalchemy.types import Date

from can.web.orm.model import *
from geopd.util import name2key

########################################################################################################################
# Tables
########################################################################################################################


user_survey_clinical_table = Table('user_survey_clinicals', Base.metadata,
                                   Column('user_id', Integer, ForeignKey('user_surveys.id'), primary_key=True),
                                   Column('clinical_id', Integer, ForeignKey('clinical_surveys.id'), primary_key=True))

user_survey_epidemiologic_table = Table('user_survey_epidemiologics', Base.metadata,
                                        Column('user_id', Integer, ForeignKey('user_surveys.id'),
                                               primary_key=True),
                                        Column('epidemiologic_id', Integer, ForeignKey('epidemiologic_surveys.id'),
                                               primary_key=True))

user_survey_biospecimen_table = Table('user_survey_biospecimens', Base.metadata,
                                      Column('user_id', Integer, ForeignKey('user_surveys.id'), primary_key=True),
                                      Column('biospecimen_id', Integer, ForeignKey('biospecimen_surveys.id'),
                                             primary_key=True))

project_investigator_table = Table('project_investigators', Base.metadata,
                                   Column('project_id', Integer, ForeignKey('projects.id'), primary_key=True),
                                   Column('investigator_id', Integer, ForeignKey('users.id'), primary_key=True))

core_leader_table = Table('core_leaders', Base.metadata,
                          Column('core_id', Integer, ForeignKey('cores.id'), primary_key=True),
                          Column('leader_id', Integer, ForeignKey('users.id'), primary_key=True))


########################################################################################################################
# Models
########################################################################################################################


class UserBio(Base):
    id = Column(Integer, ForeignKey('users.id'), primary_key=True, autoincrement=False)
    research_interests = Column(Text)
    research_experience = Column(Text)

    user = relationship('User', foreign_keys=[id], backref=backref('bio', uselist=False))

    def __init__(self, user_id):
        self.user_id = user_id

    def __repr__(self):
        return "<UserBio({0})>".format(self.user_id)


class UserSurvey(Base):
    id = Column(Integer, ForeignKey('users.id'), primary_key=True, autoincrement=False)

    ethical = Column(Boolean)
    ethical_explain = Column(Text)
    consent = Column(Boolean)
    consent_explain = Column(Text)
    consent_sharing = Column(Boolean)
    sample = Column(Boolean)
    completed_on = Column(DateTime)

    user = relationship('User', foreign_keys=[id], backref=backref('survey', uselist=False))

    clinical = relationship('ClinicalSurvey', secondary=user_survey_clinical_table)
    epidemiologic = relationship('EpidemiologicSurvey', secondary=user_survey_epidemiologic_table)
    biospecimen = relationship('BiospecimenSurvey', secondary=user_survey_biospecimen_table)

    def __init__(self, user_id):
        self.user_id = user_id

    def __repr__(self):
        return "<UserSurvey({0})>".format(self.user_id)


class ClinicalSurvey(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<ClinicalSurvey({0})>'.format(self.name)

    def __str__(self):
        return self.name


class EpidemiologicSurvey(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<EpidemiologicSurvey({0})>'.format(self.name)

    def __str__(self):
        return self.name


class BiospecimenSurvey(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<BiospecimenSurvey({0})>'.format(self.name)

    def __str__(self):
        return self.name


class Project(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text, unique=True, nullable=False)

    investigators = relationship('User', secondary=project_investigator_table)

    def __init__(self, name, description, investigators=list()):
        self.name = name
        self.description = description
        self.investigators = investigators

    def __repr__(self):
        return "<Project(key='{0}')>".format(self.name)

    def __str__(self):
        return self.name


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

    def __repr__(self):
        return "<Publication({0})>".format(self.id)

    def __str__(self):
        return self.title


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
        return name2key(self.title)

    @property
    def image_url(self):
        return url_for('web.static', filename='images/meetings/{0}.jpg'.format(self.city.lower()))

    def __repr__(self):
        return "<Meeting({0})>".format(self.title)

    def __str__(self):
        return self.title


class Core(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    key = Column(Text, nullable=False, unique=True)

    leaders = relationship('User', secondary=core_leader_table)
    posts = relationship('CorePost', back_populates='core')

    def __init__(self, name, key):
        self.name = name
        self.key = key

    @property
    def image_url(self):
        return url_for('web.static', filename='images/cores/{0}.jpg'.format(self.key))

    def __repr__(self):
        return "<Core({0})>".format(self.name)

    def __str__(self):
        return self.name


class CorePost(Base):
    id = Column(Integer, primary_key=True)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_on = Column(DateTime)
    author_id = Column(Integer, ForeignKey('users.id'))
    core_id = Column(Integer, ForeignKey('cores.id'))

    author = relationship('User', foreign_keys=[author_id], backref=backref('core_posts'))
    core = relationship('Core', foreign_keys=[core_id], back_populates='posts')

    def __init__(self, title, body):
        self.title = title
        self.body = body
        self.author = current_user

    def __repr__(self):
        return "<Core({0})>".format(self.id)

    def __str__(self):
        return "Core Post #{0}".format(self.id)
