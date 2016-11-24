from setuptools import setup, find_packages

setup(name='geopd',
      version='1.0.0',
      package_dir={'': 'src'},
      packages=find_packages('src'),
      author='Omar Zabaneh',
      author_email='zabano@gmail.com',
      install_requires=[
          'markdown',
          'biopython',
          'flask',
          'flask-bootstrap',
          'flask-wtf',
          'flask-login',
          'flask-mail',
          'flask-assets',
          'flask-moment',
          'flask-sqlalchemy',
          'sqlalchemy',
          'python-dateutil',
          'ipaddress',
          'cssmin',
          'jsmin',
          'psycopg2',
          'inflection',
          'nameparser',
          'requests',
          'binaryornot',
          'sa_jsonapi'
      ],
      include_package_data=True,
      zip_safe=False,
      entry_points={
        'console_scripts': [
            'geopd_web=geopd.core:run',
        ],
    },
)
