"""
Operational database interface.
"""
import hashlib
import os.path
import pkg_resources
from datetime import datetime
from urllib import quote_plus

from geopd.orm import db
from geopd.orm import Base
from geopd.util import name2key
from flask import request
from flask import current_app
from flask import url_for
from flask_login import UserMixin
from ipaddress import ip_address
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

from sqlalchemy.schema import Table
from sqlalchemy.schema import Column
from sqlalchemy.schema import ForeignKey
from sqlalchemy.types import Boolean
from sqlalchemy.types import DateTime
from sqlalchemy.types import Date
from sqlalchemy.types import LargeBinary
from sqlalchemy.types import Integer
from sqlalchemy.types import BigInteger
from sqlalchemy.types import Float
from sqlalchemy.types import Text
from sqlalchemy.types import String

from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import false

########################################################################################################################
# Constants
########################################################################################################################


PASSWORD_HASH_LENGTH = 128

GENDER_UNKNOWN = 0
GENDER_FEMALE = 1
GENDER_MALE = 2

USER_STATUS_PENDING = 0
USER_STATUS_ACTIVE = 1
USER_STATUS_DISABLED = 2

GRAVATAR_DEFAULT_URL = 'http://www.can.ubc.ca/avatar.png'

########################################################################################################################
# Tables
########################################################################################################################


clinical_user_info = Table('clinical_user_info', Base.metadata,
                           Column('user_id', Integer, ForeignKey('user_info.user_id'), primary_key=True),
                           Column('clinical_id', Integer, ForeignKey('clinical_info.id'), primary_key=True))

epidemiologic_user_info = Table('epidemiologic_user_info', Base.metadata,
                                Column('user_id', Integer, ForeignKey('user_info.user_id'), primary_key=True),
                                Column('epidemiologic_id', Integer, ForeignKey('epidemiologic_info.id'),
                                       primary_key=True))

biospecimen_user_info = Table('biospecimen_user_info', Base.metadata,
                              Column('user_id', Integer, ForeignKey('user_info.user_id'), primary_key=True),
                              Column('biospecimen_id', Integer, ForeignKey('biospecimen_info.id'), primary_key=True))

project_investigator_table = Table('project_investigator', Base.metadata,
                                   Column('project_id', Integer, ForeignKey('project.id'), primary_key=True),
                                   Column('investigator_id', Integer, ForeignKey('user.id'), primary_key=True))

core_leader_table = Table('core_leader', Base.metadata,
                          Column('core_id', Integer, ForeignKey('core.id'), primary_key=True),
                          Column('leader_id', Integer, ForeignKey('user.id'), primary_key=True))


########################################################################################################################
# Models
########################################################################################################################


class User(UserMixin, Base):
    __jsonapi_type__ = 'users'
    __jsonapi_fields__ = ['email', 'name', 'status', 'created_on', 'last_seen']

    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    status_id = Column(Integer, ForeignKey('user_status.id'), nullable=False,
                       default=USER_STATUS_PENDING, server_default=str(USER_STATUS_PENDING))
    institution_id = Column(Integer, ForeignKey('institution.id'), nullable=False)
    created_on = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen = Column(DateTime)
    confirmed = Column(Boolean, nullable=False, default=False, server_default=false())
    force_password_reset = Column(Boolean, nullable=False, default=False, server_default=false())

    _last_ip = Column('last_ip', BigInteger)
    _password = Column('password', String(PASSWORD_HASH_LENGTH), nullable=False)
    _avatar_hash = Column('avatar_hash', String(32), nullable=False)

    status = relationship('UserStatus', foreign_keys=[status_id])
    institution = relationship('Institution', foreign_keys=[institution_id], back_populates='users')
    info = relationship('UserInfo', primaryjoin="User.id == UserInfo.user_id", uselist=False)
    avatar = relationship('UserAvatar', primaryjoin="User.id == UserAvatar.user_id", uselist=False)

    def __init__(self, email, password, name):
        self.email = email
        self.password = password
        self.name = name.title()
        self._avatar_hash = hashlib.md5(email).hexdigest()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self._password = generate_password_hash(password)

    @property
    def last_ip(self):
        return str(ip_address(self._last_ip))

    @last_ip.setter
    def last_ip(self, ip_addr):
        self._last_ip = int(ip_address(unicode(ip_addr)))

    def is_active(self):
        return self.status_id == USER_STATUS_ACTIVE

    def check_password(self, password):
        """
        Check password against stored hash.

        :param str password: password (in clear text)
        :rtype: bool
        :return: True on success, otherwise False
        """
        return check_password_hash(self._password, password)

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.add(self)
        return True

    def gravatar(self, size=50, default=quote_plus(GRAVATAR_DEFAULT_URL), rating='g'):

        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        return '{url}/{hash}.png?s={size}&d={default}&r={rating}'.format(url=url, hash=self._avatar_hash,
                                                                         size=size, default=default, rating=rating)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        else:
            if data.get('confirm') != self.id:
                return False
            self.confirmed = True
            db.add(self)
            return True

    def ping(self):
        from flask import request
        self.last_ip = request.remote_addr
        self.last_seen = datetime.utcnow()

    def __repr__(self):
        return "<User({0})>".format(self.name)

    def __str__(self):
        return self.name


class UserStatus(Base):
    __jsonapi_fields__ = ['name']

    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)

    def __init__(self, status_id, name):
        self.id = status_id
        self.name = name

    def __repr__(self):
        return "<UserStatus({0})>".format(self.name)

    def __str__(self):
        return self.name


class UserAvatar(Base):
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True, autoincrement=False)
    data = Column(LargeBinary)
    mimetype = Column(Text)

    def __init__(self, user_id):
        self.user_id = user_id


class UserInfo(Base):
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True, autoincrement=False)

    research_interests = Column(Text)
    research_experience = Column(Text)

    ethical = Column(Boolean)
    ethical_explain = Column(Text)
    consent = Column(Boolean)
    consent_explain = Column(Text)
    consent_sharing = Column(Boolean)
    sample = Column(Boolean)

    clinical = relationship('ClinicalInfo', secondary=clinical_user_info)
    epidemiologic = relationship('EpidemiologicInfo', secondary=epidemiologic_user_info)
    biospecimen = relationship('BiospecimenInfo', secondary=biospecimen_user_info)

    def __init__(self, user_id):
        self.user_id = user_id


class ClinicalInfo(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<ClinicalInfo({0})>'.format(self.name)

    def __str__(self):
        return self.name


class EpidemiologicInfo(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<EpidemiologicInfo({0})>'.format(self.name)

    def __str__(self):
        return self.name


class BiospecimenInfo(Base):
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<BiospecimenInfo({0})>'.format(self.name)

    def __str__(self):
        return self.name


class Institution(Base):
    __jsonapi_type__ = 'institutions'
    __jsonapi_fields__ = ['name', 'url']

    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    url = Column(Text)
    city = Column(Text)
    longitude = Column(Float)
    latitude = Column(Float)

    users = relationship('User', back_populates='institution')

    def __init__(self, name, city=None, latitude=None, longitude=None, url=None):
        self.name = name
        self.city = city
        self.latitude = latitude
        self.longitude = longitude
        self.url = url

    def __repr__(self):
        return "<Institution(name='{0}')>".format(self.name)

    def __str__(self):
        return self.name


class Project(Base):
    __jsonapi_type__ = 'projects'
    __jsonapi_fields__ = ['name', 'description']

    id = Column(Integer, primary_key=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text, unique=True, nullable=False)

    investigators = relationship('User', secondary=project_investigator_table)

    def __init__(self, name, description, investigators=[]):
        self.name = name
        self.description = description
        self.investigators = investigators

    def __repr__(self):
        return "<Project(key='{0}')>".format(self.name)

    def __str__(self):
        return self.name


class Publication(Base):
    __jsonapi_type__ = 'publications'
    __jsonapi_fields__ = ['title', 'source', 'issue', 'volume', 'pages', 'authors', 'published_on', 'epublished_on']

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
            return url_for('static', filename='pubmed/{0}.pdf'.format(self.id))

    def __repr__(self):
        return "<Publication({0})>".format(self.id)

    def __str__(self):
        return self.title


class Meeting(Base):
    __jsonapi_type__ = 'meetings'
    __jsonapi_fields__ = ['city', 'year']

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
        return url_for('static', filename='images/meetings/{0}.jpg'.format(self.city.lower()))

    def __repr__(self):
        return "<Meeting({0})>".format(self.title)

    def __str__(self):
        return self.title


class Core(Base):
    __jsonapi_type__ = 'cores'
    __jsonapi_fields__ = ['name', 'key']

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False, unique=True)
    key = Column(Text, nullable=False, unique=True)

    leaders = relationship('User', secondary=core_leader_table)

    def __init__(self, name, key):
        self.name = name
        self.key = key

    @property
    def image_url(self):
        return url_for('static', filename='images/cores/{0}.jpg'.format(self.key))

    def __repr__(self):
        return "<Core({0})>".format(self.name)

    def __str__(self):
        return self.name
