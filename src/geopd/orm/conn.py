from dx import db_conn_dict, dw_conn_dict
from dx.conn import session_scope


def db_session():
    """
    Provides a transaction scope for the operational database.

    >>> with db_session() as s:
    ...     pass
    """
    return session_scope(**db_conn_dict)


def dw_session():
    """
    Provides a transaction scope for the data warehouse (dimensional database).

    >>> with dw_session() as s:
    ...     pass
    """
    return session_scope(**dw_conn_dict)
