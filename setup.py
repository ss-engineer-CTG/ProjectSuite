from setuptools import setup, find_packages

setup(
    name="ProjectSuite",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "customtkinter>=5.0.0",
        "pandas>=1.5.0",
        "dash>=2.7.0",
        "plotly>=5.10.0",
        "openpyxl>=3.0.10",
        "xlrd>=2.0.1",
        "python-docx>=0.8.11",
        "pywin32>=303;platform_system=='Windows'",
        "portalocker>=2.5.0",
    ],
    entry_points={
        'console_scripts': [
            'project-suite=ProjectManager.src.main:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['*.json', '*.csv', '*.txt'],
    },
    python_requires='>=3.8',
    author="Your Name",
    author_email="your.email@example.com",
    description="Project Management Suite with Document Processing and Dashboard",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/project-suite",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)