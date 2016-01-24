#/usr/bin/env python
import io
import re
from setuptools import setup


with io.open('./seasnake/__init__.py', encoding='utf8') as version_file:
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file.read(), re.M)
    if version_match:
        version = version_match.group(1)
    else:
        raise RuntimeError("Unable to find version string.")


with io.open('README.rst', encoding='utf8') as readme:
    long_description = readme.read()


setup(
    name='seasnake',
    version=version,
    description='A tool to manage conversion of C++ code to Python.',
    long_description=long_description,
    author='Russell Keith-Magee',
    author_email='russell@keith-magee.com',
    url='http://pybee.org/seasnake',
    packages=[
        'seasnake',
    ],
    install_requires=[
        'clang==3.7.dev257739'
    ],
    dependency_links=[
        # A patched version of clang is required for Python 3 compatibility
        'git+https://github.com/freakboy3742/python-clang.git@14eca7f47e03e65cf149cb3771e9fe30bc46f739#egg=clang-3.7.dev257739'
    ],
    entry_points={
        'console_scripts': [
            'seasnake = seasnake.__main__:main',
        ]
    },
    license='New BSD',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        # 'Programming Language :: Python :: 2',
        # 'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development',
        'Topic :: Utilities',
    ],
    test_suite='tests'
)
