from setuptools import setup, find_packages

setup (name = 'rdb',
       version = '0.2',
       description = 'Python Remote Debugger',
       author = 'Christopher Swenson',
       author_email = 'chris@caswenson.com',
       packages = ['rdb', 'rdb/templates'],
       include_package_data = True,
       package_data = {'': ['*.html']},
       url = 'http://www.github.com/swenson/python_remote_debugger',
       long_description = '''
A remote debugging framework, servers, and a client for Python.
''')
