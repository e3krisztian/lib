from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import os
import contextlib
import shutil
import tempfile


class Path(''.__class__):

    def __div__(self, other):
        return self.__class__(os.path.join(self, other))

    __truediv__ = __div__


def ensure_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)

    assert os.path.isdir(path)


def parent(path):
    return Path(os.path.normpath(Path(path) / '..'))


def write_file(path, content):
    if isinstance(content, bytes):
        f = open(path, 'wb')
    else:
        f = open(path, 'wt', encoding='utf-8')

    with f:
        f.write(content)


@contextlib.contextmanager
def temp_dir(dir):
    ensure_directory(dir)

    temp_dir = tempfile.mkdtemp(dir=dir)
    try:
        yield Path(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
