Goal: # Server Sandbox Provider Enablement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add server-owned sandbox provider enablement policy at `[server.sandbox.providers.<provider>]`, enforce it for launched runs, and make the installer write explicit provider policy entries.

**Architecture:** Model sandbox provider policy as resolved server settings, separate from run environments. Missing config remains backward-compatible by resolving all providers to enabled, while explicit false values block the corresponding effective sandbox provider at server admission, preflight, and launch.

**Tech Stack:** Rust, `serde`, existing `fabro-config` layer/resolve patterns, OpenAPI/progenitor, generated TypeScript API client, Axum server handlers, `cargo nextest`.

---

## File Structure

- Modify `lib/crates/fabro-config/src/layers/server.rs`
  - Add sparse `[server.sandbox]` layer structs with closed `providers.local`, `providers.docker`, and `providers.daytona` tables.
- Modify `lib/crates/fabro-config/src/resolve/server.rs`
  - Resolve missing sandbox provider policy to all providers enabled.
- Modify `lib/crates/fabro-types/src/settings/server.rs`
  - Add resolved `ServerSandboxSettings`, `ServerSandboxProvidersSettings`, and `ServerSandboxProviderSettings` types under `ServerNamespace`.
- Modify `lib/crates/fabro-install/src/lib.rs`
  - Make `write_sandbox_settings` write all three provider enablement tables with `enabled = true`.
- Modify `lib/crates/fabro-server/src/run_manifest.rs` and `lib/crates/fabro-server/src/server/handler/runs.rs`
  - Add policy checks for run creation and preflight.
- Modify `lib/crates/fabro-server/src/server.rs`
  - Add a launch-time recheck before sandbox setup.
- Modify `docs/public/api-reference/fabro-api.yaml`
  - Include `server.sandbox` in the `ServerSettings` API shape.
- Regenerate `lib/packages/fabro-api-client/src/models/*`
  - Include TypeScript client models for the new settings shape.
- Modify docs:
  - `docs/public/administration/server-configuration.mdx`
  - `docs/public/administration/sandboxing.mdx`

## Contract

Supported TOML shape:

```toml
[server.sandbox.providers.local]
enabled = true

[server.sandbox.providers.docker]
enabled = true

[server.sandbox.providers.daytona]
enabled = true
```

Resolution rules:

- Missing `[server.sandbox]` means all providers are enabled.
- Missing `[server.sandbox.providers]` means all providers are enabled.
- Missing individual provider tables mean that provider is enabled.
- Missing individual `enabled` values mean that provider is enabled.
- Unknown keys under `[server.sandbox]`, `[server.sandbox.providers]`, or provider tables are schema errors.

Policy rule:

- The server checks the **effective** provider, after existing dry-run coercion from Docker/Daytona to Local.
- Disabled-provider failures use this message:

```text
sandbox provider "<provider>" is disabled by server.sandbox.providers.<provider>.enabled
```

Installer rule:

- Browser install and CLI/shared install persistence keep using the chosen sandbox provider as the default run environment.
- Installer-generated `settings.toml` always writes all three sandbox provider entries with `enabled = true`.

## Task 1: Add Server Config Types and Resolution

**Files:**
- Modify: `lib/crates/fabro-config/src/layers/server.rs`
- Modify: `lib/crates/fabro-config/src/resolve/server.rs`
- Modify: `lib/crates/fabro-types/src/settings/server.rs`
- Test: `lib/crates/fabro-config/src/tests/resolve_server.rs`

- [ ] **Step 1: Write failing config tests**

Add tests in `lib/crates/fabro-config/src/tests/resolve_server.rs`:

```rust
#[test]
fn server_sandbox_defaults_all_providers_enabled() {
    let settings = super::server_settings_from_toml(
        r#"
_version = 1

[server.auth]
methods = ["dev-token"]
"#,
    );

    let sandbox = settings.server.sandbox;
    assert!(sandbox.providers.local.enabled);
    assert!(sandbox.providers.docker.enabled);
    assert!(sandbox.providers.daytona.enabled);
}

#[test]
fn server_sandbox_allows_partial_provider_overrides() {
    let settings = super::server_settings_from_toml(
        r#"
_version = 1

[server.auth]
methods = ["dev-token"]

[server.sandbox.providers.daytona]
enabled = false
"#,
    );

    let sandbox = settings.server.sandbox;
    assert!(sandbox.providers.local.enabled);
    assert!(sandbox.providers.docker.enabled);
    assert!(!sandbox.providers.daytona.enabled);
}

#[test]
fn parsing_rejects_unknown_server_sandbox_provider() {
    let err = fabro_config::ServerSettingsBuilder::from_toml(
        r#"
_version = 1

[server.auth]
methods = ["dev-token"]

[server.sandbox.providers.exe]
enabled = true
"#,
    )
    .expect_err("unknown sandbox provider should be rejected");

    assert!(
        err.to_string().contains("unknown field `exe`"),
        "unexpected error: {err}"
    );
}
```

Run:

```bash
cargo test -p fabro-config server_sandbox --quiet
cargo test -p fabro-config parsing_rejects_unknown_server_sandbox_provider --quiet
```

Expected: tests fail because `server.sandbox` does not exist yet.

- [ ] **Step 2: Add sparse config layer types**

In `lib/crates/fabro-config/src/layers/server.rs`, add `sandbox` to `ServerLayer`:

```rust
#[serde(default, skip_serializing_if = "Option::is_none")]
pub sandbox: Option<ServerSandboxLayer>,
```

Add the layer structs near the other server subdomain structs:

```rust
/// `[server.sandbox]` — server-owned sandbox provider policy.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize, fabro_macros::Combine)]
#[serde(deny_unknown_fields)]
pub struct ServerSandboxLayer {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub providers: Option<ServerSandboxProvidersLayer>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize, fabro_macros::Combine)]
#[serde(deny_unknown_fields)]
pub struct ServerSandboxProvidersLayer {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub local: Option<ServerSandboxProviderLayer>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub docker: Option<ServerSandboxProviderLayer>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub daytona: Option<ServerSandboxProviderLayer>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize, fabro_macros::Combine)]
#[serde(deny_unknown_fields)]
pub struct ServerSandboxProviderLayer {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub enabled: Option<bool>,
}
```

- [ ] **Step 3: Add resolved server settings types**

In `lib/crates/fabro-types/src/settings/server.rs`, add `sandbox` to `ServerNamespace` after `ip_allowlist` or before `storage`:

```rust
pub sandbox: ServerSandboxSettings,
```

Update `ServerNamespace::test_default()` to initialize it:

```rust
sandbox: ServerSandboxSettings::default(),
```

Add resolved structs:

```rust
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ServerSandboxSettings {
    pub providers: ServerSandboxProvidersSettings,
}

impl Default for ServerSandboxSettings {
    fn default() -> Self {
        Self {
            providers: ServerSandboxProvidersSettings::default(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ServerSandboxProvidersSettings {
    pub local:   ServerSandboxProviderSettings,
    pub docker:  ServerSandboxProviderSettings,
    pub daytona: ServerSandboxProviderSettings,
}

impl Default for ServerSandboxProvidersSettings {
    fn default() -> Self {
        Self {
            local:   ServerSandboxProviderSettings::default(),
            docker:  ServerSandboxProviderSettings::default(),
            daytona: ServerSandboxProviderSettings::default(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct ServerSandboxProviderSettings {
    pub enabled: bool,
}

impl Default for ServerSandboxProviderSettings {
    fn default() -> Self {
        Self { enabled: true }
    }
}
```

- [ ] **Step 4: Resolve the new settings**

In `lib/crates/fabro-config/src/resolve/server.rs`, import the new layer and resolved types, then add `sandbox` to `ServerNamespace` construction:

```rust
sandbox: resolve_sandbox(layer.sandbox.as_ref()),
```

Add resolver helpers:

```rust
fn resolve_sandbox(layer: Option<&ServerSandboxLayer>) -> ServerSandboxSettings {
    let providers = layer.and_then(|sandbox| sandbox.providers.as_ref());
    ServerSandboxSettings {
        providers: ServerSandboxProvidersSettings {
            local:   resolve_sandbox_provider(providers.and_then(|providers| providers.local.as_ref())),
            docker:  resolve_sandbox_provider(providers.and_then(|providers| providers.docker.as_ref())),
            daytona: resolve_sandbox_provider(providers.and_then(|providers| providers.daytona.as_ref())),
        },
    }
}

fn resolve_sandbox_provider(
    layer: Option<&ServerSandboxProviderLayer>,
) -> ServerSandboxProviderSettings {
    ServerSandboxProviderSettings {
        enabled: layer.and_then(|provider| provider.enabled).unwrap_or(true),
    }
}
```

- [ ] **Step 5: Run config tests**

Run:

```bash
cargo test -p fabro-config server_sandbox --quiet
cargo test -p fabro-config parsing_rejects_unknown_server_sandbox_provider --quiet
```

Expected: all tests pass.

## Task 2: Enforce Policy in Server Run Paths

**Files:**
- Modify: `lib/crates/fabro-server/src/run_manifest.rs`
- Modify: `lib/crates/fabro-server/src/server/handler/runs.rs`
- Modify: `lib/crates/fabro-server/src/server.rs`
- Test: `lib/crates/fabro-server/src/server/tests.rs`
- Test: `lib/crates/fabro-server/tests/it/api/runs.rs`

- [ ] **Step 1: Add the shared policy helper**

In `lib/crates/fabro-server/src/run_manifest.rs`, add this helper near `resolve_sandbox_provider`:

```rust
pub(crate) fn sandbox_provider_policy_error(
    server_settings: &fabro_types::ServerSettings,
    provider: SandboxProvider,
) -> Option<String> {
    let enabled = match provider {
        SandboxProvider::Local => server_settings.server.sandbox.providers.local.enabled,
        SandboxProvider::Docker => server_settings.server.sandbox.providers.docker.enabled,
        SandboxProvider::Daytona => server_settings.server.sandbox.providers.daytona.enabled,
    };

    (!enabled).then(|| {
        format!(
            "sandbox provider \"{provider}\" is disabled by server.sandbox.providers.{provider}.enabled"
        )
    })
}

pub(crate) fn effective_sandbox_provider(settings: &RunNamespace) -> SandboxProvider {
    let provider = resolve_sandbox_provider(settings);
    if settings.execution.mode == RunMode::DryRun && !provider.is_local() {
        SandboxProvider::Local
    } else {
        provider
    }
}
```

Replace local duplicate dry-run effective-provider logic in `build_preflight_report` with `effective_sandbox_provider(&resolved_run)`.

- [ ] **Step 2: Add preflight policy failure**

In `build_preflight_report`, after `sandbox_provider` is computed and before runtime sandbox checks:

```rust
if let Some(error) = sandbox_provider_policy_error(&server_settings, sandbox_provider) {
    checks.push(CheckResult {
        name:        "Sandbox Provider Policy".into(),
        status:      CheckStatus::Error,
        summary:     error,
        details:     Vec::new(),
        remediation: None,
    });
    return Ok((
        CheckReport {
            title:    "Run Preflight".into(),
            sections: vec![CheckSection {
                title: String::new(),
                checks,
            }],
        },
        false,
    ));
}
```

- [ ] **Step 3: Reject disabled providers at run creation**

In `lib/crates/fabro-server/src/server/handler/runs.rs`, after `prepared` is created and before parent validation:

```rust
let provider = run_manifest::effective_sandbox_provider(&prepared.settings.run);
if let Some(error) = run_manifest::sandbox_provider_policy_error(&state.server_settings(), provider)
{
    return ApiError::bad_request(error).into_response();
}
```

This deliberately uses the resolved run settings already produced by `prepare_manifest_with_environment_defaults`; sandbox provider selection is not graph-dependent.

- [ ] **Step 4: Recheck policy at launch**

In `lib/crates/fabro-server/src/server.rs`, after loading `persisted` and before resolving GitHub credentials:

```rust
let effective_provider = run_manifest::effective_sandbox_provider(&persisted.run_spec().settings.run);
if let Some(error) = run_manifest::sandbox_provider_policy_error(&server_settings, effective_provider)
{
    tracing::error!(run_id = %run_id, error = %error, "Sandbox provider disabled by server policy");
    fail_run_before_execution(&state, run_id, FailureReason::LaunchFailed, error).await;
    return;
}
```

- [ ] **Step 5: Test server behavior**

Add tests covering:

```rust
#[test]
fn sandbox_provider_policy_error_reports_disabled_provider() {
    let settings = server_settings_from_toml(
        r#"
_version = 1

[server.auth]
methods = ["dev-token"]

[server.sandbox.providers.daytona]
enabled = false
"#,
    );

    assert_eq!(
        crate::run_manifest::sandbox_provider_policy_error(
            &settings,
            fabro_sandbox::SandboxProvider::Daytona,
        )
        .as_deref(),
        Some(
            "sandbox provider \"daytona\" is disabled by server.sandbox.providers.daytona.enabled"
        )
    );
}
```

Add an API integration test in `lib/crates/fabro-server/tests/it/api/runs.rs` that creates a test app with Daytona disabled and a manifest selecting a Daytona environment. Assert `POST /api/v1/runs` returns `400` and the policy message.

Add a preflight test that sends the same manifest to `/api/v1/runs/preflight` and asserts `ok = false` plus a `Sandbox Provider Policy` error check.

Run:

```bash
cargo nextest run -p fabro-server sandbox_provider_policy
cargo nextest run -p fabro-server --test it runs::create_run_rejects_disabled_sandbox_provider
```

Expected: all new tests pass.

## Task 3: Update Installer Persistence

**Files:**
- Modify: `lib/crates/fabro-install/src/lib.rs`
- Test: `lib/crates/fabro-install/src/lib.rs`
- Test: `lib/crates/fabro-server/tests/it/api/install.rs`

- [ ] **Step 1: Add installer unit assertions**

Extend `write_sandbox_settings_records_docker_provider` and `write_sandbox_settings_records_daytona_provider` to assert all three provider policies:

```rust
fn sandbox_provider_enabled(doc: &toml::Value, provider: &str) -> Option<bool> {
    doc.get("server")
        .and_then(toml::Value::as_table)
        .and_then(|server| server.get("sandbox"))
        .and_then(toml::Value::as_table)
        .and_then(|sandbox| sandbox.get("providers"))
        .and_then(toml::Value::as_table)
        .and_then(|providers| providers.get(provider))
        .and_then(toml::Value::as_table)
        .and_then(|provider| provider.get("enabled"))
        .and_then(toml::Value::as_bool)
}

assert_eq!(sandbox_provider_enabled(&doc, "local"), Some(true));
assert_eq!(sandbox_provider_enabled(&doc, "docker"), Some(true));
assert_eq!(sandbox_provider_enabled(&doc, "daytona"), Some(true));
```

Run:

```bash
cargo test -p fabro-install write_sandbox_settings_records --quiet
```

Expected: tests fail because policy entries are not written yet.

- [ ] **Step 2: Write all provider policy entries**

Add helper functions in `lib/crates/fabro-install/src/lib.rs`:

```rust
fn write_sandbox_provider_enabled(
    providers: &mut toml::Table,
    provider: &str,
    enabled: bool,
) -> Result<()> {
    let table = ensure_table(providers, provider)?;
    table.insert("enabled".to_string(), toml::Value::Boolean(enabled));
    Ok(())
}

fn write_sandbox_provider_policy(server: &mut toml::Table) -> Result<()> {
    let sandbox = ensure_table(server, "sandbox")?;
    let providers = ensure_table(sandbox, "providers")?;
    write_sandbox_provider_enabled(providers, "local", true)?;
    write_sandbox_provider_enabled(providers, "docker", true)?;
    write_sandbox_provider_enabled(providers, "daytona", true)?;
    Ok(())
}
```

In `write_sandbox_settings`, after obtaining the root table and before returning:

```rust
let server = ensure_table(root, "server")?;
write_sandbox_provider_policy(server)?;
```

- [ ] **Step 3: Update browser install finish tests**

In `lib/crates/fabro-server/tests/it/api/install.rs`, update Docker and Daytona install finish tests to assert:

```rust
assert!(settings.contains("[server.sandbox.providers.local]"));
assert!(settings.contains("[server.sandbox.providers.docker]"));
assert!(settings.contains("[server.sandbox.providers.daytona]"));
assert!(settings.contains("enabled = true"));
```

Also parse the generated settings with `ServerSettingsBuilder::from_toml` and assert all three resolved providers are enabled.

- [ ] **Step 4: Run installer tests**

Run:

```bash
cargo test -p fabro-install write_sandbox_settings_records --quiet
cargo nextest run -p fabro-server --test it install::token_install_finish_persists_settings_env_and_vault
cargo nextest run -p fabro-server --test it install::daytona_install_finish_writes_settings_and_vault_secret
```

Expected: all tests pass.

## Task 4: Update API Schema, Generated Clients, and Docs

**Files:**
- Modify: `docs/public/api-reference/fabro-api.yaml`
- Modify: `lib/crates/fabro-api/tests/server_settings_round_trip.rs`
- Regenerate: `lib/packages/fabro-api-client/src/models/*`
- Modify: `docs/public/administration/server-configuration.mdx`
- Modify: `docs/public/administration/sandboxing.mdx`

- [ ] **Step 1: Update OpenAPI server settings schema**

In `docs/public/api-reference/fabro-api.yaml`, add `sandbox` as required on `ServerNamespace` and define:

```yaml
    ServerSandboxSettings:
      type: object
      required: [providers]
      properties:
        providers:
          $ref: "#/components/schemas/ServerSandboxProvidersSettings"

    ServerSandboxProvidersSettings:
      type: object
      required: [local, docker, daytona]
      properties:
        local:
          $ref: "#/components/schemas/ServerSandboxProviderSettings"
        docker:
          $ref: "#/components/schemas/ServerSandboxProviderSettings"
        daytona:
          $ref: "#/components/schemas/ServerSandboxProviderSettings"

    ServerSandboxProviderSettings:
      type: object
      required: [enabled]
      properties:
        enabled:
          type: boolean
```

- [ ] **Step 2: Update API round-trip test**

In `lib/crates/fabro-api/tests/server_settings_round_trip.rs`, add TOML to the sample:

```toml
[server.sandbox.providers.daytona]
enabled = false
```

Add JSON assertions:

```rust
assert_eq!(json["server"]["sandbox"]["providers"]["local"]["enabled"], true);
assert_eq!(json["server"]["sandbox"]["providers"]["docker"]["enabled"], true);
assert_eq!(json["server"]["sandbox"]["providers"]["daytona"]["enabled"], false);
```

- [ ] **Step 3: Regenerate API artifacts**

Run:

```bash
cargo build -p fabro-api
cd lib/packages/fabro-api-client && bun run generate
```

Expected: generated Rust/API and TypeScript client types include the new sandbox settings models.

- [ ] **Step 4: Update docs**

In `docs/public/administration/server-configuration.mdx`, add `[server.sandbox]` to the server-owned sections table and full reference:

```toml
[server.sandbox.providers.local]
enabled = true

[server.sandbox.providers.docker]
enabled = true

[server.sandbox.providers.daytona]
enabled = true
```

Add a short section:

```md
### `[server.sandbox.providers]` section

Controls which sandbox providers the server may launch. Missing provider entries default to `enabled = true` for backward compatibility. Disabling a provider rejects new runs whose effective provider is disabled; dry-run Docker/Daytona runs use the local provider and are governed by `server.sandbox.providers.local.enabled`.
```

In `docs/public/administration/sandboxing.mdx`, add one paragraph pointing operators to `[server.sandbox.providers.<provider>]` for enable/disable policy.

- [ ] **Step 5: Run API/docs tests**

Run:

```bash
cargo test -p fabro-api server_settings_json_matches_openapi_shape --quiet
cd apps/fabro-web && bun run typecheck
```

Expected: tests and typecheck pass.

## Task 5: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run focused Rust tests**

Run:

```bash
cargo test -p fabro-config server_sandbox --quiet
cargo test -p fabro-install write_sandbox_settings_records --quiet
cargo test -p fabro-api server_settings_json_matches_openapi_shape --quiet
cargo nextest run -p fabro-server sandbox_provider_policy
```

Expected: all focused tests pass.

- [ ] **Step 2: Run formatting and lint checks**

Run:

```bash
cargo +nightly-2026-04-14 fmt --check --all
cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings
```

Expected: both pass.

- [ ] **Step 3: Run frontend typecheck if generated TypeScript changed**

Run:

```bash
cd apps/fabro-web && bun run typecheck
```

Expected: typecheck passes.

- [ ] **Step 4: Commit**

Run:

```bash
git add lib/crates/fabro-config lib/crates/fabro-types lib/crates/fabro-install lib/crates/fabro-server docs/public lib/crates/fabro-api lib/packages/fabro-api-client apps/fabro-web
git commit -m "feat: add server sandbox provider policy"
```

Expected: commit succeeds with only intended files staged.


## Completed stages
- **toolchain**: succeeded
  - Script: `command -v cargo >/dev/null || { curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && sudo ln -sf $HOME/.cargo/bin/* /usr/local/bin/; }; cargo --version 2>&1`
  - Output:
    ```
    cargo 1.95.0 (f2d3ce0bd 2026-03-21)
    ```
- **preflight_compile**: succeeded
  - Script: `cargo check -q --workspace 2>&1`
  - Output: (empty)
- **preflight_lint**: succeeded
  - Script: `cargo +nightly-2026-04-14 clippy -q --workspace --all-targets -- -D warnings 2>&1`
  - Output: (empty)


Read the plan file referenced in the goal and implement every step. Make all the code changes described in the plan. Use red/green TDD.