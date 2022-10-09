from __future__ import absolute_import
from sio.compilers.system_gcc import CStyleCompiler


class CCompiler(CStyleCompiler):
    lang = 'c'

    @classmethod
    def gcc_10_2_1_c99(cls):
        obj = cls('gcc.10_2_1')
        obj.options = ['-std=gnu99', '-static', '-O3', '-s', '-lm']
        return obj


class CPPCompiler(CStyleCompiler):
    lang = 'cpp'

    @classmethod
    def gcc_10_2_1_cpp17(cls):
        obj = cls('gcc.10_2_1')
        obj.compiler = 'g++'
        obj.options = ['-std=c++17', '-static', '-O3', '-s', '-lm']
        return obj

def run_gcc10_2_1_c99(environ):
    return CCompiler.gcc_10_2_1_c99().compile(environ)


def run_gcc_default(environ):
    return CCompiler.gcc_10_2_1_c99().compile(environ)


def run_gplusplus10_2_1_cpp17(environ):
    return CPPCompiler.gcc_10_2_1_cpp17().compile(environ)


def run_gplusplus_default(environ):
    return CPPCompiler.gcc_10_2_1_cpp17().compile(environ)


run_c_default = run_gcc_default
run_c_gcc10_2_1_c99 = run_gcc10_2_1_c99
run_cpp_default = run_gplusplus_default
run_cpp_gcc10_2_1_cpp17 = run_gplusplus10_2_1_cpp17
