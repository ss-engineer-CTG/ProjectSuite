from setuptools import setup, find_packages

setup(
    name="CreateProjectList",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "pywin32",
        "openpyxl",
        "xlrd",
    ],
    entry_points={
        'console_scripts': [
            'CreateProjectList=CreateProjectList.main.document_processor_main:main',
        ],
    },
)