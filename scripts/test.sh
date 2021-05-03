#!/bin/sh -e

set -ex

scripts/check.sh
coverage run -m pytest tests
scripts/coverage.sh
