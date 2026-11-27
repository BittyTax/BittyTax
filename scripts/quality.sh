#!/usr/bin/env bash
set -euo pipefail

run() {
  echo "==> $*"
  "$@"
}

run isort .
run black .
run flake8 .
run pylint --spelling-dict=en_GB .
run djlint --check .
run mypy --install-types --non-interactive .

echo "All quality checks passed."
