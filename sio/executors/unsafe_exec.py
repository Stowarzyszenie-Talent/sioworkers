from __future__ import absolute_import
from sio.executors import common, interactive_common
from sio.workers.executors import Sio2JailExecutor


def run(environ):
    # This is a bit hacky patch to make unsafe-exec safe
    return common.run(environ, Sio2JailExecutor(use_perf=False))

def interactive_run(environ):
    return interactive_common.run(environ, Sio2JailExecutor(use_perf=False))
