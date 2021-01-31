#!/bin/sh

root=$(git rev-parse --show-toplevel)
max_line_lenght=$(cat "$root/setup.cfg" | grep "max-line-length" | grep -Eo '[[:digit:]]+')

black --check -l $max_line_lenght $root || exit 1
flake8 "$root" || exit 1
