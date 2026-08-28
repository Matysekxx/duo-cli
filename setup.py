from setuptools import setup, find_packages

setup(
    name="duo-cli",
    version="1.3.0",
    description="Modern Duolingo Command Line Interface and Automated Learning Engine in Python",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Duo-CLI Contributors",
    url="https://github.com/Matysekxx/duo-cli",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.31.0",
        "rich>=13.0.0",
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "duo = duo.cli:main",
            "duo-cli = duo.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Topic :: Education",
    ],
)
