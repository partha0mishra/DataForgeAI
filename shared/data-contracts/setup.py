"""Setup configuration for dataforge-contracts library."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dataforge-contracts",
    version="0.1.0",
    author="DataForge Team",
    author_email="team@dataforge.ai",
    description="Shared data contracts and schemas for DataForge AI Platform",
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
    package_dir={"": "python"},
    packages=find_packages(where="python"),
    python_requires=">=3.11",
    install_requires=[
        "pydantic>=2.0.0",
        "jsonschema>=4.17.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
            "mypy>=1.5.0",
        ],
    },
)
