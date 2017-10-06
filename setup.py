"""OBS Matcher

See:
https://github.com/sandhose/obs-matcher
"""

from codecs import open
from os import path

from setuptools import find_packages, setup

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

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
