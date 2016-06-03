import logging.handlers
import os.path

from sqlalchemy.ext.declarative import declarative_base, declared_attr

from geopd import app
from geopd.util import to_underscore
from geopd.config import config
from geopd.orm.conn import create_scoped_session
from geopd.orm.conn import db_conn_dict

db = create_scoped_session(**db_conn_dict)  #: global database connection


@app.teardown_appcontext
def shutdown_session(exception=None):
    db.remove()


class Base(object):
    @declared_attr
    def __tablename__(cls):
        return to_underscore(cls.__name__)


Base = declarative_base(cls=Base)
Base.query = db.query_property()

########################################################################################################################
# Logger
########################################################################################################################

LOGGER_INTERVAL = 'D'
LOGGER_BACKUP_COUNT = 14

sql_log_path = config.get('db.logger', 'sql_log', None)

if sql_log_path:
    log = logging.getLogger('sqlalchemy.engine')
    log.setLevel(logging.INFO)
    log.addHandler(logging.handlers.TimedRotatingFileHandler(os.path.expanduser(sql_log_path),
                                                             when=LOGGER_INTERVAL,
                                                             backupCount=LOGGER_BACKUP_COUNT))
