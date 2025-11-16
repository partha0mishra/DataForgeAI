"""Setup configuration for dataforge-connectors library."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dataforge-connectors",
    version="0.1.0",
    author="DataForge Team",
    author_email="team@dataforge.ai",
    description="Data source connectors for DataForge AI Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/dataforge-platform",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.11",
    install_requires=[
        "dataforge-common>=0.1.0",
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.0",
        "pymysql>=1.1.0",
        "boto3>=1.28.0",
        "azure-storage-blob>=12.18.0",
        "google-cloud-storage>=2.10.0",
        "snowflake-connector-python>=3.1.0",
        "google-cloud-bigquery>=3.11.0",
        "redshift-connector>=2.0.0",
        "kafka-python>=2.0.2",
        "pandas>=2.0.0",
        "pyarrow>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "moto>=4.2.0",  # AWS mocking
        ],
        "mongodb": ["pymongo>=4.5.0"],
        "cassandra": ["cassandra-driver>=3.28.0"],
        "oracle": ["cx_Oracle>=8.3.0"],
    },
)
