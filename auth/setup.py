"""Setup configuration for HireCJ Auth Service."""

from setuptools import setup, find_packages

setup(
    name="hirecj-auth",
    version="1.0.0",
    description="Authentication and OAuth service for HireCJ platform",
    author="Cratejoy, Inc.",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "fastapi>=0.109.0",
        "uvicorn[standard]>=0.27.0",
        "pydantic>=2.5.3",
        "pydantic-settings>=2.1.0",
        "httpx>=0.26.0",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.6",
        "asyncpg>=0.29.0",
        "sqlalchemy>=2.0.25",
        "alembic>=1.13.1",
        "redis>=5.0.0",
    ],
)
