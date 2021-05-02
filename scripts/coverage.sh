#!/bin/sh -e

set -x

coverage report --show-missing --skip-covered --fail-under=100
