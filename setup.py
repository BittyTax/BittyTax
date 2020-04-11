import os
import re
import io

from setuptools import setup

BITTYTAX_PATH = os.path.expanduser('~/.bittytax')
VERSION_FILE = 'bittytax/version.py'
GITHUB_REPO = 'https://github.com/BittyTax/BittyTax'

def get_version():
    line = open(VERSION_FILE, 'rt').read()
    version = re.search(r'^__version__ = [\'"]([^\'"]*)[\'"]', line, re.MULTILINE)
    if version:
        return version.group(1)
    else:
        raise RuntimeError('Unable to find version string in ' + VERSION_FILE)

def get_long_description():
    with io.open('README.md', encoding='utf8') as ld:
        return ld.read()

setup(
    name='BittyTax',
    version=get_version(),
    description='Cryptoasset accounting, auditing and UK tax calculations (Capital Gains/Income '
                'Tax)',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    url=GITHUB_REPO,
    download_url=GITHUB_REPO + '/archive/v{}.zip'.format(get_version()),
    author='Scott Green/Nano Nano Ltd',
    author_email='scott@bitty.tax',
    license='AGPLv3',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Office/Business :: Financial :: Accounting',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Natural Language :: English',
        'Operating System :: MacOS',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    keywords='bittytax cryptoasset cryptocurrency crypto tax',
    packages=['bittytax', 'bittytax.conv', 'bittytax.conv.parsers', 'bittytax.price'],
    package_data={'bittytax': ['templates/*.html']},
    install_requires=[
        'python-dateutil',
        'requests',
        'pyyaml',
        'xlrd',
        'xlsxwriter',
        'jinja2',
        'xhtml2pdf',
    ],
    entry_points={
        'console_scripts': [
            'bittytax = bittytax.bittytax:main',
            'bittytax_conv = bittytax.conv.bittytax_conv:main',
            'bittytax_price = bittytax.price.bittytax_price:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
    )
