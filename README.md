# What is this repo?
The version of sioworkers used by Stowarzyszenie Talent. 
It's deployed on wyzwania.programuj.edu.pl and
locally on camps.

See the respective branches for additional info.

# Additional features
 - support for the GCC 10.2.1 compilation sandbox,
   the one used at the Polish Olympiad in Informatics.
 - 64-bit execution, needed for the above compiler sandbox to work.
 - sio2jail executor fixes, with a newer version hardcoded.

Someday this will be made into a pull request upstream.

# INSTALLATION

### for python 2 installation ###
pip install -r requirements.txt

python setup.py install

### for python 3 installation ###
pip install -r requirements_py3.txt

python setup.py install

# TESTS

### to run all tests ###
`tox`
in main directory

### to run twisted tests (python2) ###
run:
trial sio.sioworkersd.twisted_t
in the directory of installation

### to run twisted tests (python3) ###
run:
trial sio/sioworkersd/twisted_t
in the directory of installation
