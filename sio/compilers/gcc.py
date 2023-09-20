from __future__ import absolute_import
from sio.compilers.system_gcc import CStyleCompiler


class CCompiler(CStyleCompiler):
    lang = 'c'

    @classmethod
    def gcc_12_2_0_c99(cls):
        obj = cls('gcc.12_2_0')
        obj.options = ['-std=gnu99', '-static', '-O3', '-s', '-lm']
        return obj


class CPPCompiler(CStyleCompiler):
    lang = 'cpp'

    @classmethod
    def gcc_12_2_0_cpp20(cls):
        obj = cls('gcc.12_2_0')
        obj.compiler = 'g++'
        obj.options = ['-std=c++20', '-static', '-O3', '-s', '-lm']
        return obj

def run_gcc12_2_0_c99(environ):
    return CCompiler.gcc_12_2_0_c99().compile(environ)


def run_gcc_default(environ):
    return CCompiler.gcc_12_2_0_c99().compile(environ)


def run_gplusplus12_2_0_cpp20(environ):
    return CPPCompiler.gcc_12_2_0_cpp20().compile(environ)


def run_gplusplus_default(environ):
    return CPPCompiler.gcc_12_2_0_cpp20().compile(environ)


run_c_default = run_gcc_default
run_c_gcc12_2_0_c99 = run_gcc12_2_0_c99
run_cpp_default = run_gplusplus_default
run_cpp_gcc12_2_0_cpp20 = run_gplusplus12_2_0_cpp20
