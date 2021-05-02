#!/bin/sh -e

export SOURCE_FILES="eventual tests"
set -x

autoflake --in-place --recursive $SOURCE_FILES
isort --project=eventual $SOURCE_FILES
black $SOURCE_FILES
