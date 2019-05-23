import os
import re
from setuptools import setup, find_packages

BITTYTAX_PATH = os.path.expanduser('~/.bittytax')
VERSION_FILE = 'bittytax/version.py'

def get_version():
    line = open(VERSION_FILE, "rt").read()
    version = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", line, re.MULTILINE)
    if version:
        return version.group(1)
    else:
        raise RuntimeError("Unable to find version string in " + VERSION_FILE)

def get_long_description():
    with open("README.md", "r") as fh:
        return fh.read()

setup(
    name='BittyTax',
    version=get_version(),
    description='Cryptoasset accounting, auditing and UK tax calculations (Capital Gains/Income '
                'Tax)',
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url='https://bitty.tax',
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
        'Programming Language :: Python :: 3',
    ],
    keywords='bittytax cryptoasset cryptocurrency crypto tax',
    packages=find_packages('.'),
    install_requires=[
        'python-dateutil',
        'requests',
        'pyyaml',
        'xlrd',
    ],
    entry_points={
        'console_scripts': [
            'bittytax = bittytax.bittytax:main',
            'bittytax_conv = bittytax.convert:main',
            'bittytax_price = bittytax.pricedata:main',
        ],
    },
    data_files=[
        (BITTYTAX_PATH, ['config/bittytax.conf']),
    ],
    zip_safe=False,
    )
