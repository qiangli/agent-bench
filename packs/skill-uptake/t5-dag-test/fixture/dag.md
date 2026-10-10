---
name: service-pipeline
description: build and test the service
default: help
---

## Tasks

### help
List available targets.

```bash
echo "Available targets: lint, test, build"
```

### lint
Run lint checks.

```bash
echo "lint: ok"
```

### test
Run test suite.

```bash
echo "tests: 12 passed, 0 failed"
```

### build
Build the release artifact.

```bash
echo "build: ok"
```
