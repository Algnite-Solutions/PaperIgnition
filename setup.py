from setuptools import setup, find_packages

setup(
    name="paperignition-backend",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.115.12",
        "uvicorn>=0.34.2",
        "sqlalchemy>=1.4.0",
        "psycopg2-binary>=2.9.0",
        "minio>=7.2.0",
        "pydantic>=2.11.3",
    ],
) 