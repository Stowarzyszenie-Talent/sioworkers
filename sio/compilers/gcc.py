from __future__ import absolute_import
from sio.compilers.system_gcc import CStyleCompiler


class CCompiler(CStyleCompiler):
    lang = 'c'

    @classmethod
    def gcc_14_2_0_c99(cls):
        obj = cls('gcc.14_2_0')
        obj.options = ['-std=gnu99', '-static', '-O3', '-s', '-lm']
        return obj


class CPPCompiler(CStyleCompiler):
    lang = 'cpp'

    @classmethod
    def gcc_14_2_0_cpp23(cls):
        obj = cls('gcc.14_2_0')
        obj.compiler = 'g++'
        obj.options = ['-std=c++23', '-static', '-O3', '-s', '-lm']
        return obj

def run_gcc14_2_0_c99(environ):
    return CCompiler.gcc_14_2_0_c99().compile(environ)


def run_gcc_default(environ):
    return CCompiler.gcc_14_2_0_c99().compile(environ)


def run_gplusplus14_2_0_cpp23(environ):
    return CPPCompiler.gcc_14_2_0_cpp23().compile(environ)


def run_gplusplus_default(environ):
    return CPPCompiler.gcc_14_2_0_cpp23().compile(environ)


run_c_default = run_gcc_default
run_c_gcc14_2_0_c99 = run_gcc14_2_0_c99
run_cpp_default = run_gplusplus_default
run_cpp_gcc14_2_0_cpp23 = run_gplusplus14_2_0_cpp23
