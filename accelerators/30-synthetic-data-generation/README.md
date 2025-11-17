# Accelerator 30: Synthetic Data Generation

## Overview
Privacy-preserving synthetic data generation with quality validation.

## Features
- **Generation Methods**: CTGAN, TVAE, Copula GAN
- **Privacy**: Differential privacy support
- **Quality Validation**: Statistical tests, utility scores
- **Bias Detection**: Fairness metrics
- **Multi-table**: Foreign key preservation

## Quick Start
```bash
docker build -t accelerator-30 .
docker run -p 8030:8030 accelerator-30
```

## Dependencies
- SDV 1.8.0 (synthetic data)
- Faker 22.0.0
