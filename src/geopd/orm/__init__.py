"""
This module provides an interface for relational databases.

There are two separate databases serving this package.
The first database is fully normalized and is used for operational record keeping (where data is put in from different
sources). The second is a dimensional database (i.e. data warehouse) for analytical decision making (where data is made
available to the user).

The operational database is optimized to process transactions quickly (one record at a time).
The dimensional database is optimized for high-performance queries (i.e. efficient slicing and dicing of several records
at a time). An extract-load-transform (ETL) module takes care of exporting data from the operational database
to the data warehouse. The operational database stores current data required for day-to-day operation,
while the data warehouse stores historical data.
"""
# import logging.handlers
# import os.path
#
# from dx import config
#
# ########################################################################################################################
# # Set up logger
# ########################################################################################################################
#
# LOGGER_INTERVAL = 'D'
# LOGGER_BACKUP_COUNT = 14
#
# sql_log_path = config.get('db.logger', 'sql_log', None)
#
# if sql_log_path:
#     log = logging.getLogger('sqlalchemy.engine')
#     log.setLevel(logging.INFO)
#     log.addHandler(logging.handlers.TimedRotatingFileHandler(os.path.expanduser(sql_log_path),
#                                                              when=LOGGER_INTERVAL,
#                                                              backupCount=LOGGER_BACKUP_COUNT))

