from flask import render_template
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm.exc import NoResultFound

from . import app


########################################################################################################################
# Error Handlers
########################################################################################################################


@app.errorhandler(404)
def page_not_found(e):
    return render_template('core/error.html', error='404 Not Found',
                           message='The requested page was not found.'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('core/error.html', error='500 Internal Server Error',
                           message='Unexpected error has occurred. Please try again later.'), 500


# @app.errorhandler(NoResultFound)
# def sqlalchemy_no_result_found(e):
#     return page_not_found(e)


# @app.errorhandler(SQLAlchemyError)
# def sqlalchemy_error(e):
#     db.session.rollback()
#     raise e
