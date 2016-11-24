import os
import os.path
import re
import tempfile
import shutil
import contextlib
import logging
import errno

log = logging.getLogger(__name__)


def mkdir(dir_path, mode=None):

    dir_path = os.path.abspath(dir_path)

    try:
        os.mkdir(dir_path, mode)
    except OSError as e:
        if e.errno == errno.EEXIST:
            log.warning("directory: '{0}' already exists".format(dir_path))
            if os.access(dir_path, os.W_OK):
                return dir_path
            else:
                log.error("directory: '{0}' is not writable".format(dir_path))
        raise
    else:
        log.debug("directory: '{0}' created".format(dir_path))
        return dir_path


@contextlib.contextmanager
def mkdtemp(prefix=None, dir_path=None, delete=True):
    try:
        path = mkdir(dir_path, 0700) if dir_path else tempfile.mkdtemp(prefix=prefix)
        yield path
    finally:
        if delete:
            shutil.rmtree(path)
            log.debug("temporary directory: '{0}' removed".format(path))


def find(dir_path, *exts):

    for root, dirs, files in os.walk(dir_path):

        for filename in files:
            if not exts or re.match('|'.join(['.*\.{0}$'.format(ext) for ext in exts]),
                                    filename, re.IGNORECASE):
                yield os.path.join(root, filename)

        for path in dirs:
            if path.startswith('.'):
                dirs.remove(path)