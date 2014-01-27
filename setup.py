# encoding: utf-8
from setuptools import setup

# see: http://bugs.python.org/issue15881#msg170215
try:
    import multiprocessing
except ImportError:
    pass

# prepare long_description for PyPI:
long_description = None
try:
    long_description = open('README.rst').read()
    long_description += '\n' + open('CHANGES.rst').read()
except IOError:
    pass

setup(
    name='madseq',
    version='0.1',
    description='Parser/transformator for MAD-X sequences',
    long_description=long_description,
    author='Thomas Gläßle',
    author_email='t_glaessle@gmx.de',
    maintainer='Thomas Gläßle',
    maintainer_email='t_glaessle@gmx.de',
    url='https://github.com/coldfix/madseq',
    license='MIT',
    py_modules=['madseq'],
    entry_points={
        'console_scripts': [
            'madseq = madseq:main'
        ]
    },
    install_requires=[
        'pydicti[odicti]>=0.0.3',
        'docopt'
    ],
    test_suite='nose.collector',
    tests_require=['nose'],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Intended Audience :: Science/Research',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Scientific/Engineering :: Medical Science Apps.',
        'Topic :: Scientific/Engineering :: Physics'
    ],
)
