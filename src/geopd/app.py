import os

from geopd import config, db
from geopd.orm.db import Meeting, Core
from flask import Flask
from flask import render_template, send_from_directory, redirect, url_for
from flask_login import current_user
from flask.ext.assets import Environment
from flask.ext.mail import Mail
from flask_bootstrap import Bootstrap
from flask_recaptcha import ReCaptcha
from flask_wtf import CsrfProtect


def import_blueprints():
    import geopd.error
    import geopd.auth
    import geopd.views


########################################################################################################################
# create and configure the web application
########################################################################################################################
application = Flask(__name__)
application.config.update(dict(
    SECRET_KEY=config.get('www', 'secret_key'),
    APP_BRAND=config.get('www', 'app_brand'),
    APP_NAME=config.get('www', 'app_name'),
    DEBUG=config.getboolean('www', 'debug') if config.has_option('www', 'debug') else False,
    MAIL_SERVER=config.get('mail', 'server'),
    MAIL_PORT=config.get('mail', 'port'),
    MAIL_USE_TLS=config.getboolean('mail', 'use_tls'),
    MAIL_USERNAME=os.environ.get('MAIL_USERNAME'),
    MAIL_PASSWORD=os.environ.get('MAIL_PASSWORD'),
    RECAPTCHA_SITE_KEY='6LfmDSATAAAAAAuzB4kg9Vo0vX_9xsuqaOjVDXax',
    RECAPTCHA_SECRET_KEY='6LfmDSATAAAAAKI0YXv3a8O0JnfFs6tuFZOTVGcl',
    RECAPTCHA_TYPE='image',
))

bootstrap = Bootstrap(application)
mail = Mail(application)
recaptcha = ReCaptcha(application)
csrf = CsrfProtect()

application.jinja_env.filters['datetime'] = lambda x: x.strftime('%a, %d %b %Y %X GMT')

########################################################################################################################
# web assets
########################################################################################################################
assets = Environment(application)
assets.register('js', 'js/URI.js', 'js/star-rating.js', 'js/jquery-comments.js',
                'js/validator.js', 'js/fileinput.js', 'js/jquery.jeditable.js', 'js/geopd.js',
                output='js/global.js')  # , filters='jsmin'
assets.register('css', 'css/star-rating.css', 'css/jquery-comments.css', 'css/fileinput.css',
                'css/event-list.css', 'css/funkyradio.css', 'css/geopd.css',
                output='css/global.min.css', filters='cssmin')


########################################################################################################################
# database connection handling
########################################################################################################################
@application.teardown_appcontext
def shutdown_session(exception=None):
    db.commit()
    db.remove()


########################################################################################################################
# registration of blueprints (routes, handlers, etc.)
########################################################################################################################
@application.route('/')
def index():

    if not current_user.is_anonymous:
        return redirect(url_for('web.show_member', id=current_user.id))

    return render_template('welcome.html', cores=Core.query.all(),
                           meetings=Meeting.query.filter(Meeting.carousel).order_by(Meeting.year.desc()).all())


@application.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(application.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


# @application.route('/test/')
# def test():
#     return render_template('test.html')

import_blueprints()


########################################################################################################################
# test server
########################################################################################################################
def run():
    application.run()
