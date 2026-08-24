# Python Package Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate JP FlatBuffers Python bindings and distribute them as the installable `plana-flatbuffers` package from immutable GitHub release tags.

**Architecture:** Keep `pyproject.toml` at the repository root and package the generated `python/FlatData` and `python/MX` namespace trees with `uv_build`. The existing JP generator work produces object APIs and post-processes FlatData with conversion helpers while Excel remains unencrypted. CI resolves dependencies with `uv sync`, builds a wheel, and tests that wheel in an isolated environment without committing `uv.lock` or publishing to PyPI.

**Tech Stack:** FlatBuffers 25.9.23, Python 3.10+, uv 0.12.5, uv_build, unittest, GitHub Actions, Release Please

**Spec:** `docs/superpowers/specs/2026-08-25-python-package-build-design.md`

## Global Constraints

- Distribution name is `plana-flatbuffers`; import namespaces are `FlatData` and `MX.Data.Excel`.
- Support Python 3.10 and newer; CI covers Python 3.10 and 3.14.
- Runtime dependencies remain `flatbuffers>=25.2.10` and `xxhash>=3.0.0`.
- Preserve `.scripts/compile.sh`, `.scripts/process_flatbuffers.sh`, `.scripts/process_python_object_api.py`, and `.scripts/python_conversion.py` as the JP implementation inputs.
- Generate from the repository's JP schemas and do not copy Global generated bindings.
- Do not modify generated Go files or schemas.
- Do not commit `uv.lock`; `uv sync` may create an ignored ephemeral lockfile.
- Release Please updates only `pyproject.toml` in addition to its manifest.
- Do not add PyPI publication, credentials, environments, tags, pushes, pull requests, or commits.

---

### Task 1: Establish the Python behavior and distribution contract

**Files:**
- Create: `tests/python/test_conversion.py`
- Create: `tests/python/test_object_api_processor.py`
- Create: `tests/python/test_distribution.py`
- Create: `tests/python/fixtures/ObjectApiSample.fbs`
- Create: `tests/python/fixtures/generated/TestData/__init__.py`
- Create: `tests/python/fixtures/generated/TestData/Child.py`
- Create: `tests/python/fixtures/generated/TestData/Kind.py`
- Create: `tests/python/fixtures/generated/TestData/ObjectApiSample.py.fixture`

**Interfaces:**
- Consumes: `.scripts/python_conversion.py` and `.scripts/process_python_object_api.py`.
- Produces: unittest coverage for conversion vectors, processor atomicity/idempotence, installed metadata, Release Please extra files, and representative JP imports.

- [ ] **Step 1: Port the processor fixtures and unit tests**

Copy the Global fixture suite as test-only input. Keep the fixture package name `TestData`; it is intentionally independent of either public distribution.

```powershell
Copy-Item ..\arona-flatbuffer\tests\python\test_conversion.py tests\python\test_conversion.py
Copy-Item ..\arona-flatbuffer\tests\python\test_object_api_processor.py tests\python\test_object_api_processor.py
Copy-Item ..\arona-flatbuffer\tests\python\fixtures tests\python\fixtures -Recurse
```

- [ ] **Step 2: Write the JP distribution test before generation**

Create `tests/python/test_distribution.py` with these contracts:

```python
import importlib
from importlib import metadata
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / ".release-please-manifest.json"
RELEASE_CONFIG_PATH = ROOT / "release-please-config.json"
DISTRIBUTION_NAME = "plana-flatbuffers"


class DistributionContractTests(unittest.TestCase):
    def import_or_fail(self, module_name: str):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as error:
            self.fail(f"installed distribution is missing {module_name}: {error}")

    def test_installed_version_matches_release_manifest(self):
        expected = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))["."]
        try:
            installed = metadata.version(DISTRIBUTION_NAME)
        except metadata.PackageNotFoundError:
            self.fail(f"distribution is not installed: {DISTRIBUTION_NAME}")
        self.assertEqual(installed, expected)

    def test_release_please_updates_pyproject_without_lockfile(self):
        config = json.loads(RELEASE_CONFIG_PATH.read_text(encoding="utf-8"))
        extra_files = config["packages"]["."]["extra-files"]
        self.assertEqual(
            extra_files,
            [{"type": "toml", "path": "pyproject.toml", "jsonpath": "$.project.version"}],
        )

    def test_flatdata_object_api_round_trips(self):
        module = self.import_or_fail("FlatData.BlendInfo")
        original = module.BlendInfoT(from_=11, to=29, blend=0.5)
        restored = module.BlendInfoT.from_bytes(original.to_bytes())
        self.assertEqual(restored.from_, 11)
        self.assertEqual(restored.to, 29)
        self.assertAlmostEqual(restored.blend, 0.5)

    def test_mx_namespace_is_installed(self):
        module = self.import_or_fail("MX.Data.Excel.WorldRaidStageRewardExcel")
        self.assertTrue(hasattr(module, "WorldRaidStageRewardExcelT"))
```

- [ ] **Step 3: Run the contract before generation and observe failure**

```powershell
uv run --no-project --with flatbuffers --with xxhash python -B -m unittest discover -s tests/python -v
```

Expected: processor/conversion tests pass; distribution tests fail because `plana-flatbuffers`, `FlatData`, and `MX.Data.Excel` are not installed and Release Please still mentions `uv.lock`.

- [ ] **Step 4: Review the test-only diff**

```powershell
git diff --check -- tests/python
```

Do not commit during this execution.

### Task 2: Generate and post-process JP Python bindings

**Files:**
- Preserve: `.scripts/compile.sh`
- Preserve: `.scripts/process_flatbuffers.sh`
- Preserve: `.scripts/process_python_object_api.py`
- Preserve: `.scripts/python_conversion.py`
- Generate: `python/FlatData/**/*.py`
- Generate: `python/MX/Data/Excel/**/*.py`

**Interfaces:**
- Consumes: `.schema/flatdata/*.fbs`, `.schema/excel/*.fbs`, and FlatBuffers compiler 25.9.23.
- Produces: generated object APIs plus `FlatData._conversion`, `FlatData.flatdatas_helper`, and `MX.Data.Excel.flatdatas_helper`.

- [ ] **Step 1: Obtain a matching temporary native compiler**

Download the official `Windows.flatc.binary.zip` for FlatBuffers `v25.9.23`, extract it under a temporary directory, and verify its SHA-256 against the release asset digest before execution:

```powershell
$expectedSha256 = "3d6383193ecd274f5de544a6e03464a87f581befb9fc1dda9cf508fa3cce3127"
$actualSha256 = (Get-FileHash -Algorithm SHA256 $archive).Hash.ToLowerInvariant()
if ($actualSha256 -ne $expectedSha256) { throw "flatc archive checksum mismatch" }
```

Then verify the executable itself:

```powershell
& $flatcExe --version
```

Expected: `flatc version 25.9.23`. Do not replace the repository's Linux `.scripts/flatc`.

- [ ] **Step 2: Generate only Python output from JP schemas**

Run the equivalent Python half of `.scripts/compile.sh` so existing Go output cannot change:

```powershell
Get-ChildItem .schema/flatdata -Filter *.fbs | ForEach-Object {
    & $flatcExe -o python --python --gen-object-api $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "flatc failed for $($_.FullName)" }
}
Get-ChildItem .schema/excel -Filter *.fbs | ForEach-Object {
    & $flatcExe -o python --python --gen-object-api $_.FullName
    if ($LASTEXITCODE -ne 0) { throw "flatc failed for $($_.FullName)" }
}
```

- [ ] **Step 3: Install conversion behavior and registries**

```powershell
python .scripts/process_python_object_api.py --directory python/FlatData --package FlatData
python .scripts/process_python_object_api.py --directory python/MX/Data/Excel --package MX.Data.Excel --without-decryption
```

- [ ] **Step 4: Verify representative generated APIs**

```powershell
python -m py_compile python/FlatData/BlendInfo.py python/FlatData/_conversion.py python/FlatData/flatdatas_helper.py python/MX/Data/Excel/WorldRaidStageRewardExcel.py python/MX/Data/Excel/flatdatas_helper.py
git status --short -- go .schema
```

Expected: compilation succeeds and neither `go/` nor `.schema/` changes.

### Task 3: Wire no-lock packaging, release metadata, and CI

**Files:**
- Modify: `.gitignore`
- Modify: `release-please-config.json`
- Create: `.github/workflows/python.yml`
- Verify: `pyproject.toml`

**Interfaces:**
- Consumes: generated `python/` namespaces and tests from Tasks 1-2.
- Produces: repeatable `uv sync`, wheel/sdist builds, isolated wheel import checks, and Release Please version synchronization without a lockfile updater.

- [ ] **Step 1: Ignore the ephemeral resolver output**

Append this project-specific entry near the end of `.gitignore`:

```gitignore
# uv resolves dependencies locally; libraries do not commit the lockfile.
uv.lock
```

Remove the current untracked `uv.lock` after confirming it is not tracked.

- [ ] **Step 2: Keep only the pyproject Release Please updater**

Set `packages["."].extra-files` to:

```json
[
  {
    "type": "toml",
    "path": "pyproject.toml",
    "jsonpath": "$.project.version"
  }
]
```

- [ ] **Step 3: Add Python package CI**

Create `.github/workflows/python.yml` using commit-pinned checkout and setup-uv actions, a Python `3.10`/`3.14` matrix, and these commands:

```yaml
- name: Sync project
  run: uv sync
- name: Run Python tests
  run: uv run python -B -m unittest discover -s tests/python -v
- name: Build distributions
  run: uv build --no-sources
- name: Verify wheel in an isolated environment
  shell: bash
  run: |
    set -euo pipefail
    wheel="$(find dist -maxdepth 1 -type f -name '*.whl' -print -quit)"
    test -n "$wheel"
    uv run --no-project --with "$wheel" -- python -c \
      "from FlatData.BlendInfo import BlendInfoT; from MX.Data.Excel.WorldRaidStageRewardExcel import WorldRaidStageRewardExcelT"
```

- [ ] **Step 4: Resolve, test, and build locally**

```powershell
uv sync
uv run python -B -m unittest discover -s tests/python -v
uv build --no-sources
```

Expected: all tests pass and `dist/` contains an sdist and a pure-Python wheel.

- [ ] **Step 5: Verify the wheel independently**

Create a temporary uv environment, install the built wheel, then run:

```python
from importlib.metadata import version
from FlatData.BlendInfo import BlendInfoT
from MX.Data.Excel.WorldRaidStageRewardExcel import WorldRaidStageRewardExcelT

assert version("plana-flatbuffers") == "0.13.0"
assert BlendInfoT(from_=11, to=29, blend=0.5).from_ == 11
assert WorldRaidStageRewardExcelT is not None
```

### Task 4: Document the verified Go and Python library

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: verified install, import, build, regeneration, and version commands from Tasks 2-3.
- Produces: the public installation and quickstart contract.

- [ ] **Step 1: Rewrite the README as a hybrid library landing page**

Use this structure: title and Python/Go/license badges; one-sentence description; contents; features; Python Git-tag and Go installation; `BlendInfoT` round-trip quickstart; development commands using `uv sync` without `--locked`; schema regeneration; package-vs-APK versioning; contributing; license.

The Python install command must be:

```bash
uv add git+https://github.com/arisu-archive/plana-flatbuffers --tag v0.14.0
```

State that `v0.13.0` predates the complete generated Python package and do not mention PyPI.

- [ ] **Step 2: Verify documented commands and claims**

```powershell
Select-String README.md -Pattern 'uv sync','v0.14.0','MX.Data.Excel','version.txt'
Select-String README.md -Pattern 'PyPI','--locked'
```

Expected: required claims are present; forbidden PyPI and `--locked` text is absent.

- [ ] **Step 3: Run final repository verification**

```powershell
uv run python -B -m unittest discover -s tests/python -v
uv build --no-sources
go test ./...
git diff --check
git status --short -- go .schema uv.lock
```

Expected: Python tests, build, and Go tests pass; no Go/schema/lockfile changes are included. Do not commit or push.
