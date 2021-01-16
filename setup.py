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
    description='Crypto-currency tax calculator for UK tax rules. '
                'Produces a PDF report of your capital gains and income. '
                'Import your data from popular wallets and exchanges '
                '(i.e. Coinbase, Binance, etc).',
    long_description=get_long_description(),
    long_description_content_type='text/markdown',
    url=GITHUB_REPO,
    download_url=GITHUB_REPO + '/archive/v{}.zip'.format(get_version()),
    author='Scott Green/Nano Nano Ltd',
    author_email='bittytax@nanonano.co.uk',
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    keywords='bittytax cryptoasset cryptocurrency crypto tax',
    packages=['bittytax', 'bittytax.conv', 'bittytax.conv.parsers', 'bittytax.price'],
    package_data={'bittytax': ['templates/*.html']},
    install_requires=[
        'python-dateutil>=2.7.0',
        'requests',
        'pyyaml',
        'xlrd<=1.2.0',
        'xlsxwriter',
        'jinja2',
        'xhtml2pdf',
        'colorama',
        'tqdm',
    ],
    entry_points={
        'console_scripts': [
            'bittytax = bittytax.bittytax:main',
            'bittytax_conv = bittytax.conv.bittytax_conv:main',
            'bittytax_price = bittytax.price.bittytax_price:main',
        ],
    },
    project_urls={
        'Donate': 'https://www.paypal.com/donate?hosted_button_id=HVBQW8TBEHXLC',
        'Twitter': 'https://twitter.com/bitty_tax',
        'Discord': 'https://discord.com/invite/NHE3QFt',
        'Changes': 'https://github.com/BittyTax/BittyTax/blob/master/CHANGELOG.md',
        'Source': 'https://github.com/BittyTax/BittyTax',
        'Tracker': 'https://github.com/BittyTax/BittyTax/issues',
    },
    include_package_data=True,
    zip_safe=False,
    )
