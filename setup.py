from setuptools import setup, find_packages
import sys, os

version = '1.0.0'

setup(name='gevent_queuepool',
      version=version,
      description="A db pool bases on gevent queue",
      keywords='gevent',
      author='viphxin',
      author_email='vip0hxin@gmail.com',
      url='http://www.runingman.net/',
      license='MIT',
      packages=find_packages(),
	  #scripts = [],
      # install_requires=[
      #     # -*- Extra requirements: -*-
		#   "gevent",
		#   "sqlalchemy",
      # ],
      entry_points="""
      # -*- Entry points: -*-
      """,
      )
