//! Sparse `[environments.<slug>]` and `[run.environment]` layer
//! definitions.
//!
//! An `EnvironmentLayer` describes a single reusable environment profile
//! and may appear at any config layer. The top-level `[environments]`
//! catalog merges across layers by slug.
//!
//! `RunEnvironmentLayer` is the `[run.environment]` selection: it picks an
//! environment slug via `id` and may sparsely override fields of the
//! selected environment.

use std::collections::HashMap;

use fabro_types::settings::run::DockerfileSource;
use fabro_types::settings::{Duration, EnvironmentNetworkMode, EnvironmentProvider, InterpString,
                            Size};
use serde::{Deserialize, Serialize};

use super::combine::Combine;
use super::maps::StickyMap;

/// A single `[environments.<slug>]` profile.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize, fabro_macros::Combine)]
#[serde(deny_unknown_fields)]
pub struct EnvironmentLayer {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub provider:  Option<EnvironmentProvider>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub image:     Option<EnvironmentImageLayer>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub resources: Option<EnvironmentResourcesLayer>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub network:   Option<EnvironmentNetworkLayer>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub lifecycle: Option<EnvironmentLifecycleLayer>,
    /// Sticky merge-by-key (provider-native labels).
    #[serde(default, skip_serializing_if = "StickyMap::is_empty")]
    pub labels:    StickyMap<String>,
    /// Existing volumes to mount when creating the sandbox. Replaces
    /// wholesale across layers.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub volumes:   Option<Vec<EnvironmentVolumeLayer>>,
    /// Process environment variables to set in the sandbox. Sticky
    /// merge-by-key across layers.
    #[serde(default, skip_serializing_if = "StickyMap::is_empty")]
    pub env:       StickyMap<InterpString>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize, fabro_macros::Combine)]
#[serde(deny_unknown_fields)]
pub struct EnvironmentImageLayer {
    /// Provider-native image reference (Docker image tag or Daytona
    /// snapshot name).
    #[serde(default, skip_serializing_if = "Option::is_none", rename = "ref")]
    pub image_ref:  Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub dockerfile: Option<DockerfileSource>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize, fabro_macros::Combine)]
#[serde(deny_unknown_fields)]
pub struct EnvironmentResourcesLayer {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cpu:    Option<i32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub memory: Option<Size>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub disk:   Option<Size>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize, fabro_macros::Combine)]
#[serde(deny_unknown_fields)]
pub struct EnvironmentNetworkLayer {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub mode:  Option<EnvironmentNetworkMode>,
    /// CIDR allow-list entries. Replaces wholesale across layers.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub allow: Vec<String>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize, fabro_macros::Combine)]
#[serde(deny_unknown_fields)]
pub struct EnvironmentLifecycleLayer {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub preserve:         Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub stop_on_terminal: Option<bool>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub auto_stop:        Option<Duration>,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EnvironmentVolumeLayer {
    pub id:         String,
    pub mount_path: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub subpath:    Option<String>,
}

/// `[run.environment]` — selection plus sparse overlays on the selected
/// environment.
#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize, fabro_macros::Combine)]
#[serde(deny_unknown_fields)]
pub struct RunEnvironmentLayer {
    /// Slug of the environment in the top-level `[environments]` catalog.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub id:        Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub provider:  Option<EnvironmentProvider>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub image:     Option<EnvironmentImageLayer>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub resources: Option<EnvironmentResourcesLayer>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub network:   Option<EnvironmentNetworkLayer>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub lifecycle: Option<EnvironmentLifecycleLayer>,
    #[serde(default, skip_serializing_if = "StickyMap::is_empty")]
    pub labels:    StickyMap<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub volumes:   Option<Vec<EnvironmentVolumeLayer>>,
    #[serde(default, skip_serializing_if = "StickyMap::is_empty")]
    pub env:       StickyMap<InterpString>,
}

impl RunEnvironmentLayer {
    /// Convert this overlay into an `EnvironmentLayer` (dropping `id`).
    #[must_use]
    pub fn to_environment_overlay(&self) -> EnvironmentLayer {
        EnvironmentLayer {
            provider:  self.provider,
            image:     self.image.clone(),
            resources: self.resources.clone(),
            network:   self.network.clone(),
            lifecycle: self.lifecycle.clone(),
            labels:    self.labels.clone(),
            volumes:   self.volumes.clone(),
            env:       self.env.clone(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn environment_layer_parses_full_shape() {
        let toml = r#"
provider = "daytona"

[image]
ref = "fabro-v11"

[image.dockerfile]
type = "path"
path = "Dockerfile"

[resources]
cpu = 8
memory = "16GB"
disk = "20GB"

[network]
mode = "block"
allow = ["10.0.0.0/8"]

[lifecycle]
preserve = false
stop_on_terminal = true
auto_stop = "30m"

[labels]
repo = "fabro-sh/fabro"

[[volumes]]
id = "vol-agent-state"
mount_path = "/home/daytona/agent-state"
subpath = "auth"

[env]
NODE_ENV = "development"
"#;
        let layer: EnvironmentLayer = toml::from_str(toml).expect("env layer should parse");
        assert_eq!(layer.provider, Some(EnvironmentProvider::Daytona));
        assert_eq!(
            layer.image.as_ref().and_then(|i| i.image_ref.as_deref()),
            Some("fabro-v11")
        );
        assert_eq!(layer.resources.as_ref().and_then(|r| r.cpu), Some(8));
        assert_eq!(
            layer.network.as_ref().and_then(|n| n.mode),
            Some(EnvironmentNetworkMode::Block)
        );
        assert_eq!(layer.network.as_ref().unwrap().allow, vec![
            "10.0.0.0/8".to_string()
        ]);
        assert_eq!(
            layer.lifecycle.as_ref().and_then(|l| l.preserve),
            Some(false)
        );
        assert_eq!(layer.labels.get("repo").map(String::as_str), Some("fabro-sh/fabro"));
        let volumes = layer.volumes.as_ref().expect("volumes set");
        assert_eq!(volumes.len(), 1);
        assert_eq!(volumes[0].id, "vol-agent-state");
        assert!(layer.env.contains_key("NODE_ENV"));
    }

    #[test]
    fn run_environment_layer_parses_id_with_overlays() {
        let toml = r#"
id = "fabro-dev"

[resources]
memory = "32GB"

[lifecycle]
preserve = true
"#;
        let layer: RunEnvironmentLayer = toml::from_str(toml).expect("run env layer should parse");
        assert_eq!(layer.id.as_deref(), Some("fabro-dev"));
        assert_eq!(
            layer.lifecycle.as_ref().and_then(|l| l.preserve),
            Some(true)
        );
    }

    #[test]
    fn environment_layer_combine_merges_labels_and_env_by_key() {
        let upper = EnvironmentLayer {
            labels: StickyMap::from(HashMap::from([("repo".into(), "upper".into())])),
            env: StickyMap::from(HashMap::from([(
                "NODE_ENV".into(),
                InterpString::parse("upper"),
            )])),
            ..EnvironmentLayer::default()
        };
        let lower = EnvironmentLayer {
            labels: StickyMap::from(HashMap::from([
                ("repo".into(), "lower".into()),
                ("team".into(), "lower".into()),
            ])),
            env: StickyMap::from(HashMap::from([(
                "RUST_LOG".into(),
                InterpString::parse("info"),
            )])),
            ..EnvironmentLayer::default()
        };
        let combined = upper.combine(lower);
        assert_eq!(
            combined.labels.get("repo").map(String::as_str),
            Some("upper")
        );
        assert_eq!(
            combined.labels.get("team").map(String::as_str),
            Some("lower")
        );
        assert!(combined.env.contains_key("NODE_ENV"));
        assert!(combined.env.contains_key("RUST_LOG"));
    }
}
