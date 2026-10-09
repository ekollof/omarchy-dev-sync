#!/bin/bash
set -euo pipefail
source "$(dirname "$0")/../lib/packaged-skew.sh"
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT
repo="$stage/source"
installed="$stage/installed"
mkdir -p "$repo/bin" "$repo/install/helpers" "$installed/usr/bin" "$installed/usr/share/omarchy/install/helpers"
printf 'command\n' >"$repo/bin/omarchy-test"
cp "$repo/bin/omarchy-test" "$installed/usr/bin/omarchy-test"
printf 'policy\n' >"$repo/install/helpers/usb-authorization-policy.sh"
packaged_skew "$installed"
[[ ${PACKAGED_SKEW[*]} == install/helpers/usb-authorization-policy.sh ]]
cp "$repo/install/helpers/usb-authorization-policy.sh" "$installed/usr/share/omarchy/install/helpers/usb-authorization-policy.sh"
packaged_skew "$installed"
[[ ${#PACKAGED_SKEW[@]} == 0 ]]
printf 'changed policy\n' >>"$repo/install/helpers/usb-authorization-policy.sh"
packaged_skew "$installed"
[[ ${PACKAGED_SKEW[*]} == install/helpers/usb-authorization-policy.sh ]]
cp "$repo/install/helpers/usb-authorization-policy.sh" "$installed/usr/share/omarchy/install/helpers/usb-authorization-policy.sh"
rm "$installed/usr/bin/omarchy-test"
packaged_skew "$installed"
[[ ${PACKAGED_SKEW[*]} == bin/omarchy-test ]]
printf 'outdated command\n' >"$installed/usr/bin/omarchy-test"
packaged_skew "$installed"
[[ ${PACKAGED_SKEW[*]} == bin/omarchy-test ]]
cp "$repo/bin/omarchy-test" "$installed/usr/bin/omarchy-test"
packaged_skew "$installed"
[[ ${#PACKAGED_SKEW[@]} == 0 ]]
repo="$stage/empty"
mkdir -p "$repo"
packaged_skew "$installed"
[[ ${#PACKAGED_SKEW[@]} == 0 ]]
echo 'PASS: missing and changed commands/helpers trigger refresh; matching and empty trees do not'
