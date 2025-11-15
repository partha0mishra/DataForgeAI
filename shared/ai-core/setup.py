"""Setup configuration for dataforge-ai-core library."""

from setuptools import find_packages, setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="dataforge-ai-core",
    version="0.1.0",
    author="DataForge Team",
    author_email="team@dataforge.ai",
    description="GenAI and LLM utilities for DataForge AI Platform",
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
        "openai>=1.0.0",
        "anthropic>=0.7.0",
        "langchain>=0.1.0",
        "langchain-openai>=0.0.2",
        "sentence-transformers>=2.2.0",
        "faiss-cpu>=1.7.4",
        "tiktoken>=0.5.0",
        "numpy>=1.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "pytest-asyncio>=0.21.0",
        ],
    },
)
