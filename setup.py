"""OBS Matcher

See:
https://github.com/sandhose/obs-matcher
"""

from codecs import open
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


def req(suite=None):
    suffix = '-' + suite if suite is not None else ''
    req = ''
    with open(f'requirements{suffix}.txt') as req_file:
        req = req_file.readlines()
    return req


setup(
    name='matcher',
    version='0.1.0',
    description='OBS Matcher',
    long_description=long_description,
    url='https://github.com/sandhose/obs-matcher',
    author='Quentin Gliech',
    author_email='gliech@etu.unistra.fr',
    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],

    packages=find_packages(),
    install_requires=req(),
    tests_require=req('test'),
    setup_requires=req('dev'),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'matcher=matcher.app:cli',
        ],
    },
)
