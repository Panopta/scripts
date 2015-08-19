from setuptools import setup

setup(
    name='panopta',
    version='0.1.0',
    py_modules=['panopta'],
    install_requires=[
        'click',
        'Delorean',
        'panopta_rest_api',
    ],
    dependency_links=[
        'git://github.com/Panopta/python-panopta-api-client.git@transfer-to-its-own-repo#egg=panopta_rest_api'
    ],
    entry_points={'console_scripts': ['panopta=panopta:cli']},
)
