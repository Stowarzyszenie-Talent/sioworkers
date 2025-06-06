from __future__ import absolute_import
import os
from shutil import rmtree
from zipfile import ZipFile, is_zipfile
from sio.workers import ft
from sio.workers.util import decode_fields, replace_invalid_UTF, tempcwd
from sio.workers.file_runners import get_file_runner

from sio.executors import checker
import six


def _populate_environ(renv, environ):
    """Takes interesting fields from renv into environ"""
    for key in ('time_used', 'mem_used', 'num_syscalls'):
        environ[key] = max(renv.get(key, 0), environ.get(key, 0))
    for key in ('result_code', 'result_string'):
        environ[key] = renv.get(key, '')
    if 'out_file' in renv:
        environ['out_file'] = renv['out_file']
    environ['result_percentage'] = renv.get('result_percentage', (0, 1))


def _extract_input_if_zipfile(input_name, zipdir):
    if is_zipfile(input_name):
        try:
            # If not a zip file, will pass it directly to exe
            with ZipFile(tempcwd('in'), 'r') as f:
                if len(f.namelist()) != 1:
                    raise Exception("Archive should have only one file.")

                f.extract(f.namelist()[0], zipdir)
                input_name = os.path.join(zipdir, f.namelist()[0])
        # zipfile throws some undocumented exceptions
        except Exception as e:
            raise Exception("Failed to open archive: " + six.text_type(e))

    return input_name


@decode_fields(['result_string'])
def run(environ, executor, use_sandboxes=True):
    """
    Common code for executors.
    :param: environ Recipe to pass to `filetracker` and `sio.workers.executors`
                    For all supported options, see the global documentation for
                    `sio.workers.executors` and prefix them with ``exec_``.
    :param: executor Executor instance used for executing commands.
    :param: use_sandboxes Enables safe checking output correctness.
                       See `sio.executors.checkers`. True by default.
    """

    executionCycles = environ.get('execCycle', 1)
    if not isinstance(executionCycles, int):
        executionCycles = 1
    if executionCycles < 1:
        executionCycles = 1
    environ['out_filename'] = 'out'
    if environ.get('exec_info', {}).get('mode') == 'output-only':
        renv = _fake_run_as_exe_is_output_file(environ)
        _populate_environ(renv, environ)
    else:
        inFilename = ""
        for i in range(1, executionCycles+1):
            outFilename = 'midFile_'+str(i)
            if i == executionCycles:
                outFilename = 'out'
            renv = _run(environ, executor, use_sandboxes,
                        outFilename, inFilename)
            inFilename = outFilename
            _populate_environ(renv, environ)
            environ['out_filename'] = outFilename
            if environ['result_code'] != 'OK':
                if executionCycles != 1:
                    try:
                        environ['result_string'] = environ['result_string'].decode()
                    except (UnicodeDecodeError, AttributeError):
                        pass
                    environ['result_string'] = '[execution ' + \
                        str(i)+' out of '+str(executionCycles) + \
                        '] ' + environ['result_string']
                break

    if (environ['result_code'] == 'OK' or environ.get('advanced_checher_control', False) == True) and environ.get('check_output'):
        environ = checker.run(environ, use_sandboxes=use_sandboxes)

    for key in ('result_code', 'result_string'):
        environ[key] = replace_invalid_UTF(environ[key])

    if 'out_file' in environ:
        ft.upload(
            environ,
            'out_file',
            tempcwd(environ['out_filename']),
            to_remote_store=environ.get('upload_out', False),
        )

    return environ


def _run(environ, executor, use_sandboxes, outFilename, inFilename):

    input_name = tempcwd(inFilename)
    downloadTest = False
    if inFilename == "":
        input_name = tempcwd('in')
        downloadTest = True

    file_executor = get_file_runner(executor, environ)
    exe_filename = file_executor.preferred_filename()

    ft.download(environ, 'exe_file', exe_filename, add_to_cache=True)
    os.chmod(tempcwd(exe_filename), 0o700)
    if downloadTest == True:
        ft.download(environ, 'in_file', input_name, add_to_cache=True)

    zipdir = tempcwd('in_dir')
    os.mkdir(zipdir)
    try:
        input_name = _extract_input_if_zipfile(input_name, zipdir)

        with file_executor as fe:
            with open(input_name, 'rb') as inf:
                # Open output file in append mode to allow appending
                # only to the end of the output file. Otherwise,
                # a contestant's program could modify the middle of the file.
                with open(tempcwd(outFilename), 'ab') as outf:
                    renv = fe(
                        tempcwd(exe_filename),
                        [],
                        stdin=inf,
                        stdout=outf,
                        ignore_errors=True,
                        environ=environ,
                        environ_prefix='exec_',
                    )

    finally:
        rmtree(zipdir)

    return renv


def _fake_run_as_exe_is_output_file(environ):
    # later code expects 'out' file to be present after compilation
    ft.download(environ, 'exe_file', tempcwd(environ['out_filename']))
    return {
        # copy filetracker id of 'exe_file' as 'out_file' (thanks to that checker will grab it)
        'out_file': environ['exe_file'],
        # 'result_code' is left by executor, as executor is not used
        # this variable has to be set manually
        'result_code': 'OK',
        'result_string': 'ok',
    }
