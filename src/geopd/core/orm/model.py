import bz2
import gzip
import hashlib
import os
import os.path
from datetime import datetime
from functools import partial
from mimetypes import guess_type

import enum
import inflection
from binaryornot.check import is_binary
from flask import current_app
from flask import request
from flask_login import UserMixin
from flask_login import current_user
from ipaddress import ip_address
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from nameparser import HumanName
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.sql.expression import false
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

from . import db

########################################################################################################################
# Tables
########################################################################################################################


user_permissions = db.Table('user_permissions',
                            db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
                            db.Column('permission_id', db.Integer, db.ForeignKey('permissions.id'), primary_key=True))


########################################################################################################################
# Models
########################################################################################################################


class User(UserMixin, db.Model):
    @enum.unique
    class STATUS(enum.IntEnum):
        PENDING = 0
        ACTIVE = 1
        DISABLED = 2

    PASSWORD_HASH_LENGTH = 128

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, unique=True, nullable=False)
    status_id = db.Column(db.Integer, db.ForeignKey('user_statuses.id'), nullable=False,
                          default=STATUS.PENDING.value, server_default=str(STATUS.PENDING.value))

    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime)
    confirmed = db.Column(db.Boolean, nullable=False, default=False, server_default=false())
    force_password_reset = db.Column(db.Boolean, nullable=False, default=False, server_default=false())

    _last_ip = db.Column('last_ip', db.BigInteger)
    _password = db.Column('password', db.String(PASSWORD_HASH_LENGTH), nullable=False)

    status = db.relationship('UserStatus', foreign_keys=[status_id])

    def __init__(self, email, password, name):
        self.email = email
        self.password = password
        self.name = UserName(name)
        self.avatar = UserAvatar()
        self.address = UserAddress()
        if hasattr(self, 'setup_handler'):
            self.setup_handler()

    @classmethod
    def setup(cls, func):
        cls.setup_handler = func

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
        return self.status_id == User.STATUS.ACTIVE

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
        db.session.add(self)
        return True

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
            db.session.add(self)
            return True

    def ping(self):
        self.last_ip = request.remote_addr
        self.last_seen = datetime.utcnow()


class Permission(db.Model):
    MANAGE_USER_ACCOUNT = 1

    id = db.Column(db.Integer, primary_key=True, autoincrement=False)
    title = db.Column(db.Text, nullable=False, unique=True)

    @declared_attr
    def users(cls):
        return db.relationship(User, secondary=user_permissions,
                               backref=db.backref('permissions', collection_class=attribute_mapped_collection('id')))

    def __init__(self, permission_id, title):
        self.id = permission_id
        self.title = title


class UserName(db.Model):
    __table_args__ = db.UniqueConstraint('first', 'middle', 'last'),

    id = db.Column(db.Integer, db.ForeignKey(User.id), primary_key=True, autoincrement=False)
    title = db.Column(db.Text)
    first = db.Column(db.Text, nullable=False)
    middle = db.Column(db.Text)
    last = db.Column(db.Text, nullable=False)
    suffix = db.Column(db.Text)
    nickname = db.Column(db.Text)

    user = db.relationship('User', foreign_keys=[id], backref=db.backref('name', lazy='joined', uselist=False))

    @hybrid_property
    def full(self):
        return self.first + ' ' + self.last

    @hybrid_property
    def formal(self):
        return self.last + ', ' + self.first

    def __init__(self, name_string):
        name = HumanName(name_string)
        self.title = name.title
        self.first = name.first.capitalize()
        self.middle = name.middle
        self.last = name.last.capitalize()
        self.suffix = name.suffix
        self.nickname = name.nickname


class UserStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, unique=True, nullable=False)

    def __init__(self, status_id, name):
        self.id = status_id
        self.name = name

    def __repr__(self):
        return "<UserStatus({0})>".format(self.name)

    def __str__(self):
        return self.name


class UserAvatar(db.Model):
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True, autoincrement=False)
    data = db.Column(db.LargeBinary)
    mimetype = db.Column(db.Text)

    user = db.relationship('User', foreign_keys=[id], backref=db.backref('avatar', uselist=False))

    def __repr__(self):
        return "<UserAvatar({0})>".format(self.id)


class UserAddress(db.Model):
    id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True, autoincrement=False)
    institution = db.Column(db.Text)
    department = db.Column(db.Text)
    website = db.Column(db.Text)
    street = db.Column(db.Text)
    city = db.Column(db.Text)
    region = db.Column(db.Text)
    postal = db.Column(db.Text)
    country = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    user = db.relationship('User', foreign_keys=[id], backref=db.backref('address', uselist=False))

    def load(self, form):
        self.institution = form.get('institution', None)
        self.department = form.get('department', None)
        self.country = form.get('country', None)
        self.street = form.get('street', None)
        self.city = form.get('city', None)
        self.region = form.get('region', None) if self.country in ('Canada', 'United States') else None
        self.postal = form.get('postal', None)
        self.latitude = form.get('lat', None)
        self.longitude = form.get('lng', None)

    @property
    def institution_full(self):
        return u"{0}, {1}".format(self.department, self.institution) if self.department else self.institution

    @property
    def long(self):
        if current_user.is_authenticated:
            region = u"{0} {1}".format(self.region, self.postal) if self.postal else self.region
            return ', '.join([s for s in self.street, self.city, region, self.country if s])

        return ', '.join([s for s in self.city, self.region, self.country if s])

    def __repr__(self):
        return "<UserAddress({0})>".format(self.id)


class FileMixin(object):
    """
    :var str path: absolute path to the original file
    :var int size: file size of the original file in bytes
    :var int mtime: file content modification time
    :var str md5sum: MD5 hex digest of the file content
    :var str _content: file content
    """

    MAX_SIZE = 0
    BINARY = False

    id = db.Column('id', db.Integer, primary_key=True)
    filename = db.Column(db.Text, unique=True, nullable=False)
    size = db.Column(db.BigInteger, nullable=False)
    mtime = db.Column(db.Integer, nullable=False)
    md5sum = db.Column(db.String(32), nullable=False)

    @declared_attr
    def _content(self):
        return db.deferred(db.Column('content', db.LargeBinary, nullable=True))

    @staticmethod
    def _open(filename, binary, encoding):
        if encoding == 'gzip':
            return gzip.GzipFile(filename)
        if encoding == 'bzip2':
            return bz2.BZ2File(filename)
        return open(filename, mode='rb')

    def __init__(self, filename):

        binary = is_binary(filename)
        encoding = guess_type(filename)[1]
        save_content = self.__class__.MAX_SIZE > 0

        self.filename = os.path.abspath(filename)
        st = os.stat(filename)
        self.mtime = int(st.st_mtime)
        self.size = st.st_size

        if save_content:
            if st.st_size > self.__class__.MAX_SIZE:
                raise Exception("file: '{0}' is too large".format(filename))
            self._content = ''

        chunk_size = os.statvfs(filename).f_frsize
        with self._open(filename, binary, encoding) as fp:
            md5 = hashlib.md5()
            for chunk in iter(partial(fp.read, chunk_size), b''):
                md5.update(chunk)
                if save_content:
                    self._content += chunk
            self.md5sum = md5.hexdigest()


class CommentMixin(object):

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    body = db.Column(db.Text, nullable=False)
    created_on = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    modified_on = db.Column(db.DateTime, onupdate=datetime.utcnow)

    @declared_attr
    def author_id(cls):
        return db.Column(db.Integer, db.ForeignKey(User.id), nullable=False)

    @declared_attr
    def author(cls):
        return db.relationship(User,
                               backref=db.backref('{}_comments'.format(cls.__name__.lower().replace('comment', ''))))

    @declared_attr
    def parent_id(cls):
        return db.Column(db.Integer, db.ForeignKey('{}.id'.format(inflection.tableize(cls.__name__))), nullable=True)

    @declared_attr
    def parent(cls):
        return db.relationship(cls, remote_side=[cls.id], backref=db.backref('replies'))

    @declared_attr
    def __table_args__(cls):
        return db.CheckConstraint(
            'parent_id IS NULL OR {}_id IS NULL'.format(inflection.underscore(cls.__name__.replace('Comment', '')))),

    def __int__(self, body):
        self.body = body
