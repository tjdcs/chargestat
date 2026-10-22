#!/bin/bash
# bump.sh VERSION [TAP_DIR] — write Formula/chargestat.rb for tag vVERSION into a
# homebrew-tap checkout (default: the tapped clone of tjdcs/tap). Run after
# the tag is pushed.
set -euo pipefail

version=${1:?usage: bump.sh VERSION [TAP_DIR]}
tap=${2:-$(brew --repo tjdcs/tap)}
url="https://github.com/tjdcs/chargestat/archive/refs/tags/v$version.tar.gz"
sha=$(curl -fsSL "$url" | shasum -a 256 | cut -d' ' -f1)

mkdir -p "$tap/Formula"
sed -E -e "s#/v[0-9][^/]*\.tar\.gz\"#/v$version.tar.gz\"#" \
	-e "s#sha256 \"[^\"]*\"#sha256 \"$sha\"#" \
	"$(dirname "$0")/chargestat.rb" >"$tap/Formula/chargestat.rb"
echo "wrote $tap/Formula/chargestat.rb ($version, $sha)"
