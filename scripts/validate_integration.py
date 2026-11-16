"""CI validation for the Gamified GTD custom integration (no HA install needed).

Checks:
- manifest.json: required keys, domain matches the component directory
- hacs.json present with a name
- services.yaml parses and covers exactly the SERVICE_* names from const.py
- strings.json and translations/en.json parse and have identical structure
- all Python files compile

Exit code 0 = all good, 1 = problems found (printed).
"""

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "gamified_gtd"

errors: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)


# --- manifest.json -----------------------------------------------------------
manifest = json.loads((COMPONENT / "manifest.json").read_text())
check(manifest.get("domain") == "gamified_gtd", "manifest domain must be 'gamified_gtd'")
check(COMPONENT.name == manifest.get("domain"), "component dir must match manifest domain")
for key in ("name", "version", "documentation", "codeowners", "config_flow", "iot_class"):
    check(key in manifest, f"manifest missing key: {key}")
check(manifest.get("config_flow") is True, "config_flow must be true")
check(re.fullmatch(r"\d+\.\d+\.\d+", str(manifest.get("version", ""))), "version must be semver")

# --- hacs.json ----------------------------------------------------------------
hacs = json.loads((ROOT / "hacs.json").read_text())
check("name" in hacs, "hacs.json missing name")

# --- services.yaml vs const.py SERVICE_* --------------------------------------
services_yaml = yaml.safe_load((COMPONENT / "services.yaml").read_text())
const_src = (COMPONENT / "const.py").read_text()
# const.py is pure Python — import it directly to read the SERVICE_* names.
sys.path.insert(0, str(COMPONENT))
import const  # noqa: E402

# SERVICE_* names that are actual services (the others are shared payload keys).
PAYLOAD_KEYS = {
    "SERVICE_PERSON", "SERVICE_SKILL", "SERVICE_POINTS", "SERVICE_PERK",
    "SERVICE_REWARD", "SERVICE_DECISION", "SERVICE_PROJECT",
}
expected = {
    v for k, v in vars(const).items()
    if k.startswith("SERVICE_") and k not in PAYLOAD_KEYS
}
check(set(services_yaml) == expected,
      f"services.yaml keys != SERVICE_* constants: only in yaml={set(services_yaml)-expected}, only in const={expected-set(services_yaml)}")
for svc, desc in services_yaml.items():
    check(isinstance(desc, dict) and "fields" in desc, f"service {svc} missing fields")

# --- strings.json / translations ----------------------------------------------
strings = json.loads((COMPONENT / "strings.json").read_text())
en = json.loads((COMPONENT / "translations" / "en.json").read_text())


def shape(d):
    return {k: (shape(v) if isinstance(v, dict) else type(v).__name__) for k, v in d.items()}


check(shape(strings) == shape(en), "strings.json and translations/en.json structures differ")
check("config" in strings and "options" in strings, "strings.json missing config/options")

# --- Python compile ------------------------------------------------------------
import py_compile  # noqa: E402

for py in sorted(COMPONENT.rglob("*.py")):
    try:
        py_compile.compile(str(py), doraise=True)
    except py_compile.PyCompileError as err:
        errors.append(f"compile error in {py}: {err}")

if errors:
    print("VALIDATION FAILED:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print(f"VALIDATION OK: manifest/hacs/services.yaml ({len(services_yaml)} services)/strings/{len(list(COMPONENT.rglob('*.py')))} py files")
