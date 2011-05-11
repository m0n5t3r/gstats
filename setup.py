#!/usr/bin/env python

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

config = {
    'name': 'gstats',
    'version': '0.6.1',
    'description': 'Flexible statistics gathering application, initially built for gunicorn (hence the g)',
    'author': 'Sabin Iacob',
    'author_email': 'iacobs+gst@m0n5t3r.info',
    'url': 'https://github.com/m0n5t3r/gstats',
    'download_url': 'https://github.com/m0n5t3r/gstats',
    'requires': ['pyzmq(>=2.0)'],
    'packages': ['gstats'],
    'scripts': ['scripts/gstats-collectd', 'scripts/gstatsctl'],
    'data_files': [
        ('share/munin/plugins', ['munin/gunicorn-requests_', 'munin/gunicorn-request-time_']),
        ('share/doc/gstats-0.5/examples', ['examples/gunicorn.conf.py']),
        ('share/doc/gstats-0.5', ['readme.mkd']),
    ],
    'classifiers': [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Topic :: System :: Monitoring',
        'Topic :: System :: Logging',
        'Topic :: Internet',
    ],
}

setup(**config)

