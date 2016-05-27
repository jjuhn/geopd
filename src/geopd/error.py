import os.path
import logging
import logging.handlers

from flask import request, render_template
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound

from geopd import config
from geopd.app import application, db

########################################################################################################################
# Set up logger
########################################################################################################################

LOGGER_INTERVAL = 'D'
LOGGER_BACKUP_COUNT = 14

log = logging.getLogger('dx')
log.setLevel(logging.INFO)
log.addHandler(logging.handlers.TimedRotatingFileHandler(os.path.expanduser(config.get('www', 'error_log')),
                                                         when=LOGGER_INTERVAL,
                                                         backupCount=LOGGER_BACKUP_COUNT))


########################################################################################################################
# Error Handlers
########################################################################################################################


@application.errorhandler(404)
def page_not_found(e):
    # if request.blueprint == 'api':
    #     return make_error_response(404, 'The requested resource was not found.')
    return render_template('error.html', error='404 Not Found',
                           message='The requested page was not found.'), 404


@application.errorhandler(500)
def internal_server_error(e):
    log.exception(e)
    return render_template('error.html', error='500 Internal Server Error',
                           message='Unexpected error has occurred. Please try again later.'), 500


@application.errorhandler(NoResultFound)
def sqlalchemy_no_result_found(e):
    return page_not_found(e)


@application.errorhandler(SQLAlchemyError)
def sqlalchemy_error(e):
    db.rollback()
    raise e
    log.exception(e)
    return render_template('error.html', error='500 Internal Server Error',
                           message='Unexpected error has occurred. Please try again later.')

