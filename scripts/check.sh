#!/bin/sh -e

export SOURCE_FILES="eventual tests"
set -x

black --check --diff $SOURCE_FILES
flake8 $SOURCE_FILES
mypy $SOURCE_FILES
isort --check --diff --project=httpx $SOURCE_FILES
