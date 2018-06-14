"""OBS Matcher

See:
https://github.com/sandhose/obs-matcher
"""

from codecs import open
from os import path

from setuptools import find_packages, setup

# FIXME: This is an ugly workaround for pip 10
try:  # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:  # for pip < 10
    from pip.req import parse_requirements


here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

requirements = [str(r.req) for r in
                parse_requirements('requirements.txt', session=False)]

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
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    packages=find_packages(),
    install_requires=requirements,
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'matcher=matcher.app:cli',
        ],
    },
)
