from setuptools import setup

setup(name='panopta',
      version='0.1.0',
      py_modules=['panopta'],
      install_requires=['click', 'panopta_rest_api', 'watching-testrunner'],
      entry_points='''
        [console_scripts]
        panopta=panopta:cli
      ''')
