from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.engine.url import URL


DRIVER_MYSQL = 'mysql'
DRIVER_PGSQL = 'postgresql'


def create_scoped_session(**kwargs):

    # use a dict for default values
    # to avoid the "dictionary is empty" KeyError
    defaults = dict(port=None, drivername=DRIVER_PGSQL, query=dict())
    kwargs = dict(defaults.items() + kwargs.items())

    try:
        url = URL(username=kwargs.pop('username'),  # required
                  password=kwargs.pop('password'),  # required
                  host=kwargs.pop('host'),  # required
                  database=kwargs.pop('database'),  # required

                  # optional argument
                  # (no need to provide a default as an argument here, see above)
                  port=kwargs.pop('port'),
                  drivername=kwargs.pop('drivername'),
                  query=kwargs.pop('query'))

    except KeyError as e:
        # a required argument is missing
        raise TypeError("missing argument: {0}".format(e.args[0]))

    return scoped_session(sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=create_engine(url, convert_unicode=True, connect_args=kwargs),
    ))


@contextmanager
def session_scope(**kwargs):
    """
    Provide a transactional scope around a series of operations.

    This function uses :func:`sqlalchemy.orm.scoped_session` and is thread safe.
    .. note:: The same session instance is returned if called multiple times in the same thread.

    Keyword Arguments:

        * username (str): the user name (required)
        * password (str): database password (required)
        * host (str): the name of the host (required)
        * database (str): the database name (required)
        * port (int): the port number (optional)
        * drivername (str): one of DRIVER_MYSQL, DRIVER_PGSQL (default), or SQLAlchemy driver name (optional)
        * query (dict): extra options to be passed to the database engine (e.g. application_name)

    Raises:
        * :exc:`TypeError` if user dose not provide a required argument
        * :exc:`TypeError` if user provide unsupported arguments

    >>> from dx import db_conn_dict
    >>> from dx.conn import session_scope
    >>> with session_scope(**db_conn_dict) as s:
    ...     pass

    """

    session = create_scoped_session(**kwargs)

    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


