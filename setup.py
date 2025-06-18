from setuptools import setup, find_packages

setup(
    name="fdic-omg",
    packages=find_packages(),
    package_data={
        'fdic_omg': ['*.py'],
    },
)