from setuptools import setup, find_packages

from disco import VERSION

with open('requirements.txt') as f:
    requirements = f.readlines()

with open('README.md') as f:
    readme = f.read()

setup(
    name='disco-py',
    author='b1nzy',
    url='https://github.com/b1naryth1ef/disco',
    version=VERSION,
    packages=find_packages(),
    license='MIT',
    description='A Python library for Discord',
    long_description=readme,
    include_package_data=True,
    install_requires=requirements,
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: MIT License',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Internet',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities',
    ])
