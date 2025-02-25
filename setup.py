"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

with  open(path.join(here, 'progressBarDistributed', '__init__.py'), encoding='utf-8') as f:
    version = f.readline().split("=")[-1].strip().strip('"')

setup(
    name='progressBarDistributed',
    version=version,
    description='A version of tqdm to be executed on distributed setups',
    long_description=long_description,  # Optional
    url='https://github.com/rsanchezgarc/tqdmDistributed',  # Optional
    author='Ruben Sanchez Garcia',  # Optional
    author_email='ruben.sanchez-garcia@stats.ox.ac.uk',  # Optional
    keywords='tqdm distributed socket multiprocessing',  # Optional
    packages=find_packages(),
    install_requires=[requirements],
    include_package_data=True,  # This line is important to read MANIFEST.in
    long_description_content_type = "text/markdown",
)
