# AGENTS.md

This file provides orientation for AI agents (Claude, Cursor, CodeRabbit, etc.) working in the `kessel-sdk-py` repository -- a Python gRPC/REST SDK for [Project Kessel](https://github.com/project-kessel) services.

## Detailed Guidelines

The following guideline files contain in-depth, domain-specific rules. Read the relevant file before working in that area.

- `docs/security-guidelines.md` -- gRPC channel security, OIDC constraints, token lifecycle, RBAC org_id validation
- `docs/performance-guidelines.md` -- Async/sync selection, streaming pagination, bulk APIs, consistency modes
- `docs/error-handling-guidelines.md` -- gRPC status codes, streaming errors, CheckBulk per-item errors, HTTP/auth errors
- `docs/api-contracts-guidelines.md` -- v1beta2 type conventions, shared reference types, backward compatibility, protobuf runtime
- `docs/testing-guidelines.md` -- Mocking patterns, async test patterns, assertions, test boundaries
- `docs/integration-guidelines.md` -- New service setup, RBAC REST API, multi-protocol coordination, env vars

## Repository Structure

```
pyproject.toml          # Package metadata, dependencies, black/flake8 config
buf.gen.yaml            # Protobuf code generation config (buf.build)
.flake8                 # Flake8 settings (max-line-length=100, excludes *_pb2*)
.github/
  workflows/
    test.yml            # pytest on push/PR to main (Python 3.11)
    lint.yml            # black --check + flake8 on push/PR to main
    build.yml           # python -m build on push/PR to main
    buf-generate.yml    # Auto-regen protobuf every 6 hours, opens PR if changed
  dependabot.yml        # Daily pip + github-actions dependency checks
src/
  kessel/
    __init__.py                     # Empty
    auth/
      __init__.py                   # Public exports for auth module
      auth.py                       # OAuth2ClientCredentials, OIDC discovery, AuthRequest
    grpc/
      __init__.py                   # oauth2_call_credentials() adapter
    middleware/
      __init__.py                   # Empty (reserved for future use)
    inventory/
      __init__.py                   # ClientBuilder base class, client_builder_for_stub()
      v1/
        __init__.py                 # ClientBuilder for health service
        *_pb2.py / *_pb2_grpc.py    # GENERATED -- health protos
      v1beta1/                      # GENERATED -- deprecated, do not extend
      v1beta2/
        __init__.py                 # ClientBuilder for KesselInventoryService
        *_pb2.py / *_pb2_grpc.py    # GENERATED -- current API protos
    console/
      __init__.py                   # x-rh-identity header helpers (principal_from_rh_identity)
    rbac/
      __init__.py                   # Empty
      v2/
        __init__.py                 # Workspace, list_workspaces, REST helpers, factory functions
  buf/validate/                     # GENERATED -- buf.validate protos
  google/                           # GENERATED -- google.api protos
examples/                           # Runnable example scripts
tests/                              # Unit tests (pytest)
```

## Generated vs. Hand-Written Code

This distinction is critical. Agents must never edit generated files.

**Generated (by `buf generate`):**
- All `*_pb2.py`, `*_pb2_grpc.py`, `*.pyi` files
- Everything under `src/buf/` and `src/google/`
- Everything under `src/kessel/inventory/v1beta1/`
- The `*_pb2.py` and `*_pb2_grpc.py` files under `src/kessel/inventory/v1/` and `src/kessel/inventory/v1beta2/`

**Hand-written (editable):**
- `src/kessel/inventory/__init__.py` -- ClientBuilder base class
- `src/kessel/inventory/v1/__init__.py` -- v1 ClientBuilder
- `src/kessel/inventory/v1beta2/__init__.py` -- v1beta2 ClientBuilder
- `src/kessel/auth/auth.py` -- OAuth2 implementation
- `src/kessel/auth/__init__.py` -- Auth public API
- `src/kessel/grpc/__init__.py` -- gRPC credential adapter
- `src/kessel/console/__init__.py` -- x-rh-identity header to SubjectReference helpers
- `src/kessel/rbac/v2/__init__.py` -- RBAC helpers and workspace functions
- `src/kessel/middleware/__init__.py` -- Empty, reserved
- `examples/*.py` -- Example scripts
- `tests/*.py` -- Unit tests

## Code Style and Formatting

- **Formatter**: black, line length 100, target Python 3.13
- **Linter**: flake8, line length 100
- **Always exclude generated files** from formatting and linting:
  - black: `black --exclude '.*_pb2(_grpc)?\.py' src/ examples/`
  - flake8: `flake8 --exclude '*_pb2.py,*_pb2_grpc.py' src/ examples/`
- The `tests/` directory is not currently included in the black/flake8 CI commands, but tests should still follow the same style conventions.
- Configuration lives in `pyproject.toml` (`[tool.black]`) and `.flake8`.

## Naming Conventions

- **Files**: snake_case for all Python files.
- **Classes**: PascalCase (`ClientBuilder`, `OAuth2ClientCredentials`, `Workspace`).
- **Functions**: snake_case (`fetch_oidc_discovery`, `list_workspaces`, `principal_subject`).
- **Test files**: `test_<module_or_feature>.py` in `tests/`.
- **Test functions**: `test_<behavior_description>` with a docstring on every test.
- **Test classes**: `Test<ClassName>` or `Test<FeatureName>` for grouping. Plain classes, not `unittest.TestCase`.
- **Constants/env vars**: UPPER_SNAKE_CASE (`AUTH_CLIENT_ID`, `KESSEL_ENDPOINT`).

## Package Management

- Build system: setuptools (via `pyproject.toml`).
- Python >= 3.11 required.
- Source layout: `src/` directory (`package-dir = {"" = "src"}`).
- **Core dependencies** (always installed): `protobuf>=6.31.1,<6.34.0`, `types-protobuf~=6.30`, `grpcio`.
- **Optional `[auth]`** (for OAuth2): `google-auth`, `requests-oauthlib`, `requests`. Do not move these into core dependencies.
- **Optional `[dev]`** (for development): `flake8~=7.3.0`, `black~=25.12.0`, `pytest`, `pytest-asyncio`.
- Install for development: `pip install -e ".[dev,auth]"`
- Auth imports in library code must use `TYPE_CHECKING` guards to avoid failing at import time when auth extras are not installed.

## CI Checks (GitHub Actions)

Three workflows run on every push/PR to `main`. All must pass.

| Workflow | File | What it does |
|----------|------|--------------|
| Test | `test.yml` | `pip install -e ".[dev,auth]"` then `pytest` |
| Lint | `lint.yml` | `black --check` and `flake8` on `src/` and `examples/` (excludes `*_pb2*`) |
| Build | `build.yml` | `python -m build`, verifies `.whl` and `.tar.gz` are created |

A fourth workflow (`buf-generate.yml`) runs on a schedule (every 6 hours) and on manual dispatch. It regenerates protobuf files and auto-creates a PR if anything changed.

## PR Expectations

- All three CI checks (test, lint, build) must pass.
- Run `black` and `flake8` locally before pushing (with the generated-file exclusions).
- Run `pytest` locally before pushing.
- Never commit credentials, secrets, or `.env` files.
- Never manually edit `*_pb2.py` or `*_pb2_grpc.py` files.
- New dependencies must have version pins/ranges in `pyproject.toml`.

## Common Pitfalls and Anti-Patterns

1. **Editing generated protobuf files.** These are overwritten by `buf generate`. To change API contracts, modify the upstream `buf.build/project-kessel/inventory-api` repository, then regenerate.

2. **Forgetting to exclude generated files from black/flake8.** Always use the exclusion patterns. CI will fail otherwise because generated code does not conform to black formatting.

3. **Importing `kessel.auth` without `TYPE_CHECKING` guards.** The auth module depends on optional extras. Library code must use `if TYPE_CHECKING:` for auth type imports. Only import auth modules at runtime inside functions that need them (see `kessel/grpc/__init__.py` for the pattern).

4. **Building on `v1beta1`.** This API version is deprecated. All new features must use `v1beta2` which has the unified `KesselInventoryService`.

5. **Mixing sync and async channels.** Channels from `build()` (sync) and `build_async()` (async) are not interchangeable. Do not pass one to patterns designed for the other.

6. **Creating gRPC channels per request.** Channel creation is expensive. Build once and reuse the `(stub, channel)` tuple.

7. **Hardcoding credentials or token endpoints.** Use environment variables for secrets. Use `fetch_oidc_discovery()` for token endpoints.

8. **Catching bare `Exception` for gRPC calls.** Always catch `grpc.RpcError` specifically.

9. **Ignoring per-item errors in bulk responses.** `CheckBulk` can succeed at the RPC level while individual items have errors. Check `pair.HasField("error")` for each pair.

## Key Architectural Patterns

- **`client_builder_for_stub()`**: Factory function that creates a version-specific `ClientBuilder` subclass from a gRPC stub class. Used in each API version's `__init__.py`.
- **Fluent builder**: `ClientBuilder` uses method chaining (`ClientBuilder(target).insecure().build()`).
- **Dual-protocol SDK**: gRPC for inventory operations, REST (`requests`) for RBAC workspace queries. Both share a single `OAuth2ClientCredentials` instance.
- **`google-auth` adapter**: `GoogleOAuth2ClientCredentials` adapts the SDK's `OAuth2ClientCredentials` to the `google.auth.credentials.Credentials` interface for gRPC auth metadata injection.

## Maintaining Examples

When adding or changing public API surface, agents must create or update corresponding example scripts in `examples/`.

### When to add or update examples

- **New SDK method or service**: Add a new example demonstrating basic usage.
- **Changed method signature or behavior**: Update any existing example that calls the affected API.
- **New authentication or connection pattern**: Add an example showing the new pattern end-to-end.
- **Deprecated API replaced**: Update examples to use the replacement; remove references to the deprecated path.

### Conventions

- **Directory**: All examples live in `examples/` at the repository root.
- **Naming**: `snake_case.py` — name the file after the feature or operation it demonstrates (e.g., `check.py`, `report_resource.py`, `rbac_list_workspaces.py`).
- **Runnable scripts**: Each example must be a standalone script that can be executed directly (`python examples/<name>.py`). Use `if __name__ == "__main__": run()` (sync) or `if __name__ == "__main__": asyncio.run(run())` (async).
- **Environment variables for configuration**: Use `os.environ.get()` for endpoints, credentials, and other runtime config (e.g., `KESSEL_ENDPOINT`, `AUTH_CLIENT_ID`). Never hardcode secrets.
- **ClientBuilder pattern**: Demonstrate the fluent builder (`ClientBuilder(target).insecure().build()` or `.oauth2_client_authenticated(creds).build()`).
- **Error handling**: Catch `grpc.RpcError` specifically — never bare `except Exception`.
- **Channel lifecycle**: Always close channels via context manager — `with channel:` for sync (`.build()`) or `async with channel:` for async (`.build_async()`). Unclosed channels leak connections and file descriptors.
- **Print output**: Print results to stdout so users can see what the API returns.
- **Not automated tests**: Examples require a live Kessel server and are not run in CI. Unit tests belong in `tests/`.

### Linting

Examples are included in CI lint checks. Run formatting and linting before committing:

```bash
black --exclude '.*_pb2(_grpc)?\.py' src/ examples/
flake8 --exclude '*_pb2.py,*_pb2_grpc.py' src/ examples/
```

## Quick Reference Commands

```bash
# Install for development
pip install -e ".[dev,auth]"

# Run tests
pytest

# Format code (exclude generated files)
black --exclude '.*_pb2(_grpc)?\.py' src/ examples/

# Lint code (exclude generated files)
flake8 --exclude '*_pb2.py,*_pb2_grpc.py' src/ examples/

# Regenerate protobuf code from upstream
buf generate

# Build package
python -m build
```
