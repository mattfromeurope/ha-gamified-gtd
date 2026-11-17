#!/usr/bin/env bash
# Rebuilds the vendored lit bundle used by the custom cards:
#   custom_components/gamified_gtd/www/gamified-gtd-lit.js
#
# Why this exists: HA's index.html only exposes "lit" via an import map on recent
# frontend versions (>= 2025.12). On older versions a static `import ... from "lit"`
# in the card module fails with "Failed to resolve module specifier" and NO card is
# registered ("Custom element not found"). The cards module therefore loads lit via
# dynamic import("lit") with a fallback to this vendored bundle.
#
# Run this only when the lit version should be bumped. The result is checked in,
# because HA serves www/ directly — users never run a build.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO_ROOT/custom_components/gamified_gtd/www/gamified-gtd-lit.js"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
cd "$TMP"

# Install lit (the library the HA frontend itself is built with) + esbuild.
npm install lit@3 esbuild --no-audit --no-fund

# Bundle all of lit's public exports into a single ES module.
printf 'export * from "lit";\n' > lit-entry.js
./node_modules/.bin/esbuild lit-entry.js \
  --bundle --format=esm --minify \
  --define:process.env.NODE_ENV='"production"' \
  --outfile=bundle-raw.js

# Prepend a banner with the exact lit version + license note (lit is MIT).
node - "$OUT" <<'NODE_EOF'
const fs = require("fs");
const [out, ...rest] = process.argv.slice(2);
const v = JSON.parse(fs.readFileSync("node_modules/lit/package.json", "utf8")).version;
const banner =
  "/* Vendored lit v" + v +
  " (MIT License, (c) Lit contributors, https://github.com/lit/lit) - bundled so the " +
  "Gamified GTD cards also load on HA versions whose index.html has no \"lit\" import map. " +
  "Rebuild with scripts/build_cards_lit.sh */\n";
fs.writeFileSync(out, banner + fs.readFileSync("bundle-raw.js", "utf8"));
console.log("wrote " + out + " (lit v" + v + ")");
NODE_EOF
