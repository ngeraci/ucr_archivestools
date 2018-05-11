# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
setup(
    name='aspace_tools',
    version="0.2",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests', 'lxml'
    ],
    entry_points={
        'console_scripts': [
            'oac-process = aspace_tools.oac_process:main',
        ]
    }
)
