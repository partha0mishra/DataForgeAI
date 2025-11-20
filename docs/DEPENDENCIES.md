# DataForge AI Platform - Dependency Management Guide

## Overview

This document explains the dependency management strategy for the DataForge AI platform, including known conflicts, compatibility matrices, and best practices.

## Quick Reference

### Installation Commands

```bash
# Install with constraints (recommended for most accelerators)
pip install -r requirements.txt -c ../../constraints.txt

# Install shared libraries
pip install -e ../../shared/common
pip install -e ../../shared/connectors
pip install -e ../../shared/ai-core  # Only if needed
pip install -e ../../shared/data-contracts  # Only if needed
```

## Shared Libraries

### Canonical Locations

The platform has shared libraries in two locations due to legacy reasons. Use the **primary** location for new development:

| Library | Primary Location | Legacy Location | Status |
|---------|-----------------|-----------------|--------|
| dataforge-common | `shared-libraries/dataforge-common/` | `shared/common/` | Use primary |
| dataforge-ai-core | `shared-libraries/dataforge-ai-core/` | `shared/ai-core/` | Use primary |
| dataforge-connectors | `shared/connectors/` | N/A | Active |
| dataforge-contracts | `shared/data-contracts/` | N/A | Active |

### Shared Library Dependencies

#### dataforge-common (Primary)
```
pydantic>=2.0.0
pydantic-settings>=2.0.0
sqlalchemy>=2.0.0
fastapi>=0.104.0
redis>=5.0.0
alembic>=1.13.0
opentelemetry-*>=1.20.0
```

#### dataforge-connectors
```
dataforge-common>=0.1.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0
boto3>=1.28.0
pandas>=2.0.0
snowflake-connector-python>=3.1.0
google-cloud-bigquery>=3.11.0
```

#### dataforge-ai-core
```
openai>=1.0.0
anthropic>=0.7.0
langchain>=0.1.0 (in legacy version)
sentence-transformers>=2.2.0 (in legacy version)
```

#### dataforge-contracts
```
pydantic>=2.0.0
jsonschema>=4.17.0
pyyaml>=6.0
```

## Critical Dependency Conflicts

### 🔴 BLOCKING: Apache Airflow Incompatibility

**Affected Accelerator:** `01-pipeline-automation`

**Problem:**
- Apache Airflow 2.7.3 requires **Pydantic v1** and **SQLAlchemy 1.4.x**
- All shared libraries require **Pydantic >=2.0.0** and **SQLAlchemy >=2.0.0**
- These versions are fundamentally incompatible (breaking API changes)

**Solution:**
The Airflow accelerator MUST be deployed in an isolated environment:

```bash
# Option 1: Separate virtual environment
python -m venv venv-airflow
source venv-airflow/bin/activate
cd accelerators/01-pipeline-automation
pip install -r requirements-airflow.txt

# Option 2: Docker container (recommended)
docker build -t dataforge-airflow -f Dockerfile.airflow .
docker run -d dataforge-airflow

# Option 3: Run API-only mode without Airflow
pip install -r requirements-api.txt
pip install -e ../../shared/common
pip install -e ../../shared/connectors
```

**DO NOT** attempt to install Airflow with other accelerators in the same environment.

## Accelerator Compatibility Matrix

### Compatible Together

These accelerator groups can be installed in the same environment:

**Group A: API-focused accelerators (Range-based versions)**
- 02-data-quality-governance
- 03-knowledge-repository
- 04-data-catalog
- 05-model-factory
- 06-bi-dashboarding
- 07-data-storytelling
- 08-conversational-analytics
- 09-process-optimization
- 10-data-monetization
- 11-proposal-accelerator
- 12-data-governance
- 13-streaming-analytics
- 14-data-observability

**Group B: Service-oriented accelerators (Pinned versions)**
- 15-mlops-automation
- 25-data-mesh-enablement
- 26-advanced-security-zero-trust
- 27-data-sharing-collaboration
- 28-graph-analytics-knowledge-graphs
- 29-geospatial-timeseries-analytics
- 30-synthetic-data-generation
- 31-aiops-intelligent-observability
- 32-disaster-recovery-multi-region

**Special Cases (Install separately)**
- 01-pipeline-automation (Airflow conflict)
- 23-ai-explainability (large ML dependencies)
- 24-cross-platform-portability (TensorFlow + PyTorch)

### Incompatible Combinations

| Accelerator 1 | Accelerator 2 | Reason | Workaround |
|---------------|---------------|--------|------------|
| 01-pipeline-automation | ANY | Airflow requires old dependencies | Isolate in Docker |
| 23-ai-explainability | 24-cross-platform-portability | Both pin different ML library versions | Separate environments |

## Deployment Strategies

### Strategy 1: Microservices Architecture (Recommended)

Deploy each accelerator in its own container/environment:

```yaml
# docker-compose.yml example
services:
  pipeline-api:
    build: ./accelerators/01-pipeline-automation
    environment:
      - MODE=api-only

  data-quality:
    build: ./accelerators/02-data-quality-governance

  catalog:
    build: ./accelerators/04-data-catalog
```

**Pros:**
- No dependency conflicts
- Independent scaling
- Isolated failures
- Easier updates

**Cons:**
- More resource usage
- More containers to manage

### Strategy 2: Shared Environment with Constraints

Install compatible accelerators together using constraints:

```bash
# Create shared environment
python -m venv venv-dataforge
source venv-dataforge/bin/activate

# Install multiple compatible accelerators
pip install -c constraints.txt \
  -r accelerators/02-data-quality-governance/requirements.txt \
  -r accelerators/04-data-catalog/requirements.txt \
  -r accelerators/05-model-factory/requirements.txt

# Install shared libraries
pip install -e shared/common -e shared/connectors
```

**Pros:**
- Less resource usage
- Simpler deployment
- Shared code

**Cons:**
- Potential conflicts
- More complex dependency resolution
- All-or-nothing updates

### Strategy 3: Hybrid Approach

- Core platform services in shared environment
- Airflow isolated in Docker
- ML-heavy accelerators isolated
- Lightweight accelerators can share

## Best Practices

### For Accelerator Development

1. **Use constraints.txt**
   ```bash
   pip install -r requirements.txt -c ../../constraints.txt
   ```

2. **Pin versions for production**
   - Use `==` for critical dependencies
   - Use `>=,<` for minor versions
   - Test thoroughly before deploying

3. **Document special requirements**
   - Add README section for conflicts
   - Update this file with new issues
   - Provide Docker/isolation instructions

4. **Test dependency installation**
   ```bash
   # In CI/CD
   pip install --dry-run -r requirements.txt
   ```

### For Platform Maintenance

1. **Regular dependency audits**
   ```bash
   # Check for security vulnerabilities
   pip-audit

   # Check for outdated packages
   pip list --outdated
   ```

2. **Update constraints.txt**
   - Review quarterly
   - Test all accelerators
   - Update pinned versions

3. **Monitor for breaking changes**
   - Subscribe to package changelogs
   - Test beta versions in dev
   - Plan migration windows

## Dependency Resolution Order

When pip resolves dependencies, it processes them in order:

1. Direct requirements from requirements.txt
2. Constraints from constraints.txt (bounds)
3. Sub-dependencies from installed packages

To debug conflicts:

```bash
# See dependency tree
pip install pipdeptree
pipdeptree

# Check specific package dependencies
pip show <package-name>

# Dry run to see what would be installed
pip install --dry-run -r requirements.txt
```

## Version Pinning Strategy

### Current Strategy (Hybrid)

- **Shared libraries:** Use ranges (`>=2.0.0,<3.0.0`)
- **Accelerators (Group A):** Use ranges (`>=0.104.0`)
- **Accelerators (Group B):** Use pins (`==2.5.3`)
- **Constraints file:** Bounds ranges (`>=2.0.0,<2.3.0`)

### Rationale

- **Ranges in shared libs:** Flexibility for different accelerators
- **Pins in accelerators:** Predictable deployments
- **Constraints:** Prevent incompatible major versions

## Migration Plans

### Apache Airflow 3.x Migration

**Timeline:** When Airflow 3.0 is stable (target: 2025 Q2)

**Changes:**
- Airflow 3.0 will support Pydantic v2 and SQLAlchemy 2.0
- Will allow integration with shared libraries
- Plan migration testing in Q1 2025

**Action Items:**
- [ ] Monitor Airflow 3.0 development
- [ ] Test beta releases
- [ ] Update requirements when stable
- [ ] Remove isolation requirements

### Shared Library Consolidation

**Timeline:** Next major release

**Changes:**
- Remove legacy locations (`shared/common/`, `shared/ai-core/`)
- Keep only primary locations
- Update all accelerator references

**Action Items:**
- [ ] Audit all imports
- [ ] Update requirements.txt references
- [ ] Migrate code if needed
- [ ] Remove legacy directories

## Troubleshooting

### Error: "Cannot install packages due to conflicting dependencies"

**Cause:** Incompatible version requirements

**Solutions:**
1. Check if mixing Airflow with other accelerators → Isolate Airflow
2. Use constraints.txt: `pip install -r requirements.txt -c ../../constraints.txt`
3. Create fresh virtual environment
4. Check for duplicate packages in requirements

### Error: "No module named 'dataforge_common'"

**Cause:** Shared library not installed

**Solution:**
```bash
pip install -e ../../shared/common
```

### Error: "ImportError: cannot import name 'BaseSettings' from 'pydantic'"

**Cause:** Pydantic v1 vs v2 incompatibility

**Solution:**
- Check if Airflow is installed → It requires Pydantic v1
- Update code to use `pydantic-settings` for v2
- Or isolate in Airflow-only environment

### Error: "Module 'sqlalchemy' has no attribute 'declarative_base'"

**Cause:** SQLAlchemy 1.x vs 2.x API changes

**Solution:**
- Update code: `from sqlalchemy.orm import declarative_base`
- Or use SQLAlchemy 1.4.x for Airflow environments

## Resources

- [Pydantic v1 to v2 Migration Guide](https://docs.pydantic.dev/latest/migration/)
- [SQLAlchemy 2.0 Migration Guide](https://docs.sqlalchemy.org/en/20/changelog/migration_20.html)
- [Apache Airflow 3.0 Roadmap](https://airflow.apache.org/)
- [pip Dependency Resolution](https://pip.pypa.io/en/stable/topics/dependency-resolution/)

## Support

For dependency issues:
1. Check this document
2. Review accelerator-specific README
3. Check GitHub issues
4. Create new issue with full error output and environment details
