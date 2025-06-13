"""Setup script for HireCJ Editor Backend."""

from setuptools import setup, find_packages

setup(
    name="hirecj-editor-backend",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi==0.104.1",
        "uvicorn[standard]==0.24.0",
        "pydantic==2.5.0",
        "pydantic-settings==2.1.0",
        "python-dotenv==1.0.0",
        "PyYAML==6.0.1",
    ],
    python_requires=">=3.8",
    author="HireCJ Team",
    description="Backend API service for HireCJ Agent Editor",
)