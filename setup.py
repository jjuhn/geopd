from setuptools import setup, find_packages

setup(name='geopd',
      version='1.0.0',
      package_dir={'': 'src'},
      packages=find_packages('src'),
      author='Omar Zabaneh',
      author_email='zabano@gmail.com',
      install_requires=[
          'setuptools',
          'can.web',
          'markdown',
          'biopython',
      ],
      include_package_data=True,
      zip_safe=False,
      entry_points={
        'console_scripts': [
            'geopd_web=geopd.web:run',
        ],
    },
)
