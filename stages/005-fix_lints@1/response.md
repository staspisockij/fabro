Clippy passes cleanly. The fix:

Added the missing `expected_secret_name` field to the two `Provider` struct initializers in `lib/crates/fabro-api/tests/provider_round_trip.rs`:

- In `provider_json_matches_openapi_shape`: set to `Some("ANTHROPIC_API_KEY".to_string())` to match Anthropic's vault credential, plus a matching `assert_eq!` on the serialized JSON.
- In `provider_omits_optional_fields_when_absent`: set to `None` with an additional assertion that the field is omitted from the serialized JSON (it's marked `#[serde(skip_serializing_if = "Option::is_none")]`).

`cargo +nightly-2026-04-14 clippy --workspace --all-targets -- -D warnings` now succeeds with exit code 0.