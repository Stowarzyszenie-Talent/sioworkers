from __future__ import absolute_import
from sio.executors import common
from sio.workers.executors import Sio2JailExecutor


def run(environ):
    # This is a bit hacky patch to make unsafe-exec safe
    return common.run(environ, Sio2JailExecutor(use_perf=False))
