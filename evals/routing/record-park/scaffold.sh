#!/usr/bin/env bash
# A minimal vault, so the session-start hook reports Tier 1 and routing is what gets tested.
set -e
mkdir -p augment_wiki notes/_inbox
printf 'house_language: en\nsource_root: notes\n' > augment_wiki/config.yaml
