# Python Package Build Design

## Objective

Make the JP-generated FlatBuffers bindings installable from immutable GitHub
release tags as the `plana-flatbuffers` Python distribution. The implementation
must preserve the repository's Go API, the existing generated namespaces, and
the in-progress Python generator changes already present in the working tree.

The current package version is `0.13.0`. The separate `version.txt` value remains
the source APK/schema version and is not a Python distribution version.

## Existing state and ownership

The repository already contains tracked `pyproject.toml` metadata for
`plana-flatbuffers`, but it does not contain a generated `python/` tree, Python
tests, or Python CI. The working tree also contains user-owned generator work in:

- `.scripts/compile.sh`
- `.scripts/process_flatbuffers.sh`
- `.scripts/process_python_object_api.py`
- `.scripts/python_conversion.py`

Those changes are inputs to this work. They will be preserved and validated,
not replaced wholesale from the Global repository.

## Public package contract

- Distribution name: `plana-flatbuffers`.
- Supported Python versions: Python 3.10 and newer.
- Import namespaces: `FlatData` and `MX.Data.Excel`.
- Runtime dependencies: `flatbuffers>=25.2.10` and `xxhash>=3.0.0`.
- The wheel contains both generated namespace trees and remains pure Python.
- Consumers install an immutable GitHub tag with uv, for example:

  ```bash
  uv add git+https://github.com/arisu-archive/plana-flatbuffers --tag v0.14.0
  ```

The existing `v0.13.0` tag predates the complete Python package. The first
documented Git-installable release is therefore expected to be `v0.14.0`.

## Packaging architecture

The existing root `pyproject.toml` remains the authoritative build and runtime
dependency definition. `uv_build` packages `python/FlatData` and `python/MX`
without relocating generated code.

No `uv.lock` is committed. This repository is a library, and consumers resolve
their own environment from `pyproject.toml`; the repository lockfile would only
control contributor and CI resolution while coupling every generated release
version change to another file. Development and CI use `uv sync`, which creates
an ephemeral local resolution as needed.

## Generation flow

The in-progress compile script generates Python object APIs alongside the Go
bindings. The processor then adds the shared conversion behavior to
`python/FlatData` and creates the `FlatData` registry. Excel bindings under
`python/MX/Data/Excel` receive object APIs and registry generation without the
FlatData decryption layer.

The initial Python tree is generated from this repository's JP schemas rather
than copied from another region. Existing Go output is compared before and
after generation; unrelated Go changes are not included.

The schema-generation workflow already stages `python/`, so future schema
updates continue refreshing the generated Python bindings once the generator
changes land.

## Continuous integration

A dedicated Python workflow runs on pull requests and pushes to `master`. It
uses commit-pinned GitHub Actions and tests Python 3.10 plus Python 3.14. Each
matrix job:

1. Installs the pinned uv tool version and requested Python version.
2. Runs `uv sync` without a committed lockfile.
3. Runs the complete Python test suite.
4. Builds the source distribution and wheel with `uv build --no-sources`.
5. Installs the built wheel into an isolated environment.
6. Imports representative modules from both public namespaces.

The isolated install prevents an editable checkout from concealing missing
wheel contents.

## Release flow

Release Please remains responsible for GitHub version bumps, tags, and releases.
Its configuration adds `pyproject.toml` as the sole extra TOML version file, so
release pull requests update `project.version` together with the manifest.

There is no package-registry publication job, deployment environment, OIDC
permission, or publishing credential. GitHub release tags are the distribution
boundary.

## Tests

The Python suite ports the Global repository's conversion and object-API
processor coverage while executing against the JP scripts and generated files.
The distribution contract additionally verifies:

- installed metadata uses the name `plana-flatbuffers`;
- installed version matches `.release-please-manifest.json`;
- representative modules from `FlatData` and `MX.Data.Excel` import;
- a real generated object serializes and deserializes without losing values;
- Release Please is configured to update `pyproject.toml` and no lockfile.

Tests are introduced before the missing generated package/CI wiring is completed
so the initial failure demonstrates the absent distribution contract.

## Documentation

The README becomes a hybrid Go/Python landing page. It documents Git-tag
installation with uv, a tested Python object-API example, Go installation,
development commands without `--locked`, schema regeneration, and the distinction
between package-release and APK/schema versions. It does not mention PyPI.

## Acceptance criteria

- JP schemas produce importable `FlatData` and `MX.Data.Excel` Python modules.
- `uv sync` installs `plana-flatbuffers` and its runtime dependencies.
- All Python tests pass on the supported-version matrix.
- `uv build --no-sources` produces an sdist and pure-Python wheel.
- An isolated environment installs the wheel and imports both namespaces.
- Release Please updates `pyproject.toml` and the release manifest without a
  lockfile freshness failure.
- The README's install and usage examples match verified behavior.
- Existing user-owned generator edits are preserved, and no unrelated Go or
  schema changes are introduced.

## Exclusions and residual risks

- No registry publication or external account configuration is included.
- No release, tag, push, pull request, or commit is created without separate
  authorization.
- With no committed lockfile, CI intentionally resolves the newest dependency
  versions allowed by `pyproject.toml`; an upstream-compatible release can change
  the CI environment between runs.
- Local generation depends on the bundled FlatBuffers compiler and a compatible
  Bash environment. If that toolchain cannot run locally, generation must occur
  in the repository's Linux automation rather than copying another region's
  generated bindings.
