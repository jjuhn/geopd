from datetime import datetime, date
from importlib import import_module

import inflection
from flask import Blueprint
from flask import Flask
from flask import render_template
from flask.json import JSONEncoder
from flask_assets import Environment
from flask_bootstrap import Bootstrap
from flask_mail import Mail
from flask_mail import Message
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CsrfProtect
from markdown import markdown
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import declared_attr

from sa_jsonapi import serializer as jsonapi


class CustomModel(object):
    @declared_attr
    def __tablename__(cls):
        return inflection.tableize(cls.__name__)

    def __repr__(self):
        return "<{0}({1})>".format(self.__class__.__name__, self.id)


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            # convert all dates to the ISO format (assume UTC without timezone)
            if isinstance(obj, datetime):
                return obj.isoformat() + 'Z'
            elif isinstance(obj, date):
                return obj.isoformat()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


app = Flask(__name__.split('.')[0])

# load default and application configuration
app.config.from_object('{0}.config'.format(__name__))  # e.g. dx.core.config
app.config.from_envvar('{0}_CONFIG_PATH'.format(app.import_name.upper()))  # e.g. DX_CONFIG_PATH
app.config['IMPORT_NAME'] = app.import_name

# json encoder
app.json_encoder = CustomJSONEncoder

# flask plugins
Bootstrap(app)
CsrfProtect(app)
mail = Mail(app)
assets = Environment(app)

# configure assets
assets.register('js',
                'core/js/URI.js',
                'core/js/star-rating.js',
                'core/js/jquery-comments.js',
                'core/js/validator.js',
                'core/js/fileinput.js',
                'core/js/jquery.jeditable.js',
                'core/js/markdown.js',
                'core/js/to-markdown.js',
                'core/js/bootstrap-markdown.js',
                'core/js/jsonapi.js',
                'core/js/core.js',
                'js/{0}.js'.format(app.import_name),
                output='js/global.js')  # jsmin?

assets.register('css',
                'core/css/star-rating.css',
                'core/css/jquery-comments.css',
                'core/css/fileinput.css',
                'core/css/event-list.css',
                'core/css/funkyradio.css',
                'core/css/bootstrap-markdown.css',
                'core/css/core.css',
                'css/{0}.css'.format(app.import_name),
                output='css/global.min.css', filters='cssmin')


# send mail
def send_email(to, subject, template_name, **context):
    subject = "[{0}] {1}".format(app.config['APP_NAME'], subject)
    msg = Message(subject,
                  sender='"{0}" <{1}>'.format(app.config['APP_NAME'], app.config['MAIL_USERNAME']),
                  recipients=[to])
    msg.body = render_template(template_name + '.txt', **context)
    msg.html = render_template(template_name + '.html', **context)
    if mail:
        mail.send(msg)


# filters
app.jinja_env.filters['isoformat'] = lambda x: x.isoformat() + 'Z'
app.jinja_env.filters['md2html'] = lambda x: markdown(x)
app.jinja_env.filters['singularize'] = lambda x: inflection.singularize(x)
app.jinja_env.filters['pluralize'] = lambda x: inflection.pluralize(x)

# sqlalchemy
db = SQLAlchemy(app)
db.Model = declarative_base(cls=CustomModel)
db.Model.query = db.session.query_property()

# core handlers
import_module('{0}.auth'.format(__name__))
import_module('{0}.error'.format(__name__))
import_module('{0}.view'.format(__name__))

# app views
import_module('{0}.view'.format(app.import_name))

# api
api = Blueprint('api', app.import_name, url_prefix='/api')
import_module('{0}.api'.format(app.import_name))
app.register_blueprint(api)
jsonapi.register_base(db.Model)

# wsgi hook
application = app


# test server
def run():
    app.run()
