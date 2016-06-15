import os

from flask import Flask
from flask_assets import Environment
from flask_bootstrap import Bootstrap
from flask_wtf import CsrfProtect

from geopd.config import config

app = Flask(__name__)

########################################################################################################################
# configure app
########################################################################################################################
app.config.update(dict(
    SECRET_KEY=config.get('www', 'secret_key'),
    APP_CODE=config.get('www', 'app_code'),
    APP_BRAND=config.get('www', 'app_brand'),
    APP_NAME=config.get('www', 'app_name'),
    DEBUG=config.getboolean('www', 'debug') if config.has_option('www', 'debug') else False,
    MAIL_SERVER=config.get('mail', 'server'),
    MAIL_PORT=config.get('mail', 'port'),
    MAIL_USE_TLS=config.getboolean('mail', 'use_tls'),
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    RECAPTCHA_USE_SSL=config.getboolean('www.recaptcha', 'use_ssl'),
    RECAPTCHA_PUBLIC_KEY=config.get('www.recaptcha', 'public_key'),
    RECAPTCHA_PRIVATE_KEY=config.get('www.recaptcha', 'private_key'),
))

########################################################################################################################
# import blueprints
########################################################################################################################

import geopd.auth
import geopd.error
import geopd.view
import geopd.api

########################################################################################################################
# helpers
########################################################################################################################
bootstrap = Bootstrap(app)
csrf = CsrfProtect(app)

########################################################################################################################
# web assets
########################################################################################################################
assets = Environment(app)

assets.register('js',
                'js/URI.js',
                'js/star-rating.js',
                'js/jquery-comments.js',
                'js/validator.js',
                'js/fileinput.js',
                'js/jquery.jeditable.js',
                'js/markdown.js',
                'js/to-markdown.js',
                'js/bootstrap-markdown.js',
                'js/jsonapi.js',
                'js/geopd.js',
                output='js/global.js')  # jsmin?

assets.register('css',
                'css/star-rating.css',
                'css/jquery-comments.css',
                'css/fileinput.css',
                'css/event-list.css',
                'css/funkyradio.css',
                'css/bootstrap-markdown.css',
                'css/geopd.css',
                output='css/global.min.css', filters='cssmin')

########################################################################################################################
# jinja2 configuration
########################################################################################################################
app.jinja_env.globals['geopd'] = config
app.jinja_env.filters['datetime'] = lambda x: x.strftime('%a, %d %b %Y %X GMT')
