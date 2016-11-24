import logging
import os

from .. import db

if 'DEBUG' in os.environ and 'sql' in os.environ['DEBUG'].split(','):
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
