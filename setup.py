"""OBS Matcher

See:
https://github.com/sandhose/obs-matcher
"""

from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='matcher',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.1.0',

    description='OBS Matcher',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/sandhose/obs-matcher',

    # Author details
    author='Quentin Gliech',
    author_email='gliech@etu.unistra.fr',

    # Choose your license
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        # 'Programming Language :: Python :: 2', # Maybe later.
        # 'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    packages=find_packages(),
    install_requires=requirements,
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'matcher=matcher.__main__:run',
        ],
    },
)
