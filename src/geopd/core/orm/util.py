import locale
import logging

from .. import db

_CHUNK_SIZE = 10000

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
locale.setlocale(locale.LC_ALL, 'en_US')


def bulk_insert(mapper, mapping, chunk_size=_CHUNK_SIZE):
    for i in xrange(0, len(mapping), chunk_size):
        batch = mapping[i:i + chunk_size]
        db.session.bulk_insert_mappings(mapper, batch)
        db.session.flush()
        total = locale.format("%d", i + len(batch), grouping=True)
        log.info("inserted {0} {1} records".format(total, mapper.__name__))
