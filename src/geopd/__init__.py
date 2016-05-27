import ConfigParser
import os.path
import atexit

from geopd.conn import create_scoped_session
from geopd.util import to_underscore
from sqlalchemy.ext.declarative import declarative_base, declared_attr

CONFIG_FILE_VAR_NAME = 'GEOPD_CONFIG_PATH'

if CONFIG_FILE_VAR_NAME not in os.environ:
    raise RuntimeError("environment variable {0} is not set".format(CONFIG_FILE_VAR_NAME))

try:
    with open(os.environ[CONFIG_FILE_VAR_NAME]) as config_file:
        config = ConfigParser.ConfigParser()
        config.readfp(config_file)
except EnvironmentError as e:
    raise RuntimeError("failed to load configuration: {0}".format(e))

try:
    db_conn_dict = dict(config.items('db'))
except ConfigParser.NoSectionError as e:
    raise RuntimeError("failed to load database configuration: {0}".format(e))

db = create_scoped_session(**db_conn_dict)  #: global database connection


def commit():
    global db
    try:
        db.commit()
    except:
        db.rollback()
        raise


@atexit.register
def close():
    global db
    db.close()


class Base(object):
    @declared_attr
    def __tablename__(cls):
        return to_underscore(cls.__name__)


Base = declarative_base(cls=Base)
Base.query = db.query_property()
