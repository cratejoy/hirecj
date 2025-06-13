"""Setup file for shared module."""

from setuptools import setup, find_packages

setup(
    name="hirecj-shared",
    version="0.1.0",
    description="Shared utilities for HireCJ services",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.5.0",
        "python-dotenv>=1.0.0",
        "sqlalchemy>=2.0.0",
    ],
)