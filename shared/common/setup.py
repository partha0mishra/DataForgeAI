"""Setup configuration for dataforge-common library."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dataforge-common",
    version="0.1.0",
    author="DataForge Team",
    author_email="team@dataforge.ai",
    description="Common utilities for DataForge AI Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/dataforge-platform",
    project_urls={
        "Bug Tracker": "https://github.com/yourorg/dataforge-platform/issues",
        "Documentation": "https://docs.dataforge.ai",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "pyjwt>=2.8.0",
        "cryptography>=41.0.0",
        "python-dotenv>=1.0.0",
        "structlog>=23.1.0",
        "opentelemetry-api>=1.20.0",
        "opentelemetry-sdk>=1.20.0",
        "opentelemetry-instrumentation>=0.41b0",
        "opentelemetry-exporter-otlp>=1.20.0",
        "prometheus-client>=0.17.0",
        "requests>=2.31.0",
        "httpx>=0.24.0",
        "tenacity>=8.2.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
        ],
    },
)
