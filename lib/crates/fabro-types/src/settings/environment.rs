//! Environment domain.
//!
//! A named environment is reusable desired configuration that describes how
//! a run should be executed: which provider, what image, what resources,
//! what network policy, lifecycle, labels, volumes, and environment
//! variables. Environments live in the top-level `[environments.<slug>]`
//! catalog and a run selects one via `[run.environment].id`.
//!
//! These dense types are the resolved view consumed by the workflow engine
//! and server preflight. Sparse, layer-mergeable counterparts live in
//! `fabro_config::layers::environment`.

use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use super::duration::Duration;
use super::interp::InterpString;
use super::run::DockerfileSource;
use super::size::Size;

/// A resolved, named environment.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EnvironmentSettings {
    pub provider:  EnvironmentProvider,
    #[serde(default, skip_serializing_if = "EnvironmentImageSettings::is_empty")]
    pub image:     EnvironmentImageSettings,
    #[serde(default, skip_serializing_if = "EnvironmentResourcesSettings::is_empty")]
    pub resources: EnvironmentResourcesSettings,
    #[serde(default, skip_serializing_if = "EnvironmentNetworkSettings::is_default")]
    pub network:   EnvironmentNetworkSettings,
    #[serde(default, skip_serializing_if = "EnvironmentLifecycleSettings::is_default")]
    pub lifecycle: EnvironmentLifecycleSettings,
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub labels:    HashMap<String, String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub volumes:   Vec<EnvironmentVolumeSettings>,
    #[serde(default, skip_serializing_if = "HashMap::is_empty")]
    pub env:       HashMap<String, InterpString>,
}

impl Default for EnvironmentSettings {
    fn default() -> Self {
        Self {
            provider:  EnvironmentProvider::Local,
            image:     EnvironmentImageSettings::default(),
            resources: EnvironmentResourcesSettings::default(),
            network:   EnvironmentNetworkSettings::default(),
            lifecycle: EnvironmentLifecycleSettings::default(),
            labels:    HashMap::new(),
            volumes:   Vec::new(),
            env:       HashMap::new(),
        }
    }
}

/// The runtime provider responsible for materializing an environment.
#[derive(
    Debug,
    Clone,
    Copy,
    PartialEq,
    Eq,
    Serialize,
    Deserialize,
    strum::Display,
    strum::EnumString,
    strum::IntoStaticStr,
)]
#[serde(rename_all = "snake_case")]
#[strum(serialize_all = "snake_case")]
pub enum EnvironmentProvider {
    Local,
    Docker,
    Daytona,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct EnvironmentImageSettings {
    /// Provider-native image reference (Docker image tag or Daytona
    /// snapshot name).
    #[serde(default, skip_serializing_if = "Option::is_none", rename = "ref")]
    pub image_ref:  Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub dockerfile: Option<DockerfileSource>,
}

impl EnvironmentImageSettings {
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.image_ref.is_none() && self.dockerfile.is_none()
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct EnvironmentResourcesSettings {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub cpu:    Option<i32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub memory: Option<Size>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub disk:   Option<Size>,
}

impl EnvironmentResourcesSettings {
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.cpu.is_none() && self.memory.is_none() && self.disk.is_none()
    }
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EnvironmentNetworkSettings {
    pub mode:  EnvironmentNetworkMode,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub allow: Vec<String>,
}

impl Default for EnvironmentNetworkSettings {
    fn default() -> Self {
        Self {
            mode:  EnvironmentNetworkMode::AllowAll,
            allow: Vec::new(),
        }
    }
}

impl EnvironmentNetworkSettings {
    #[must_use]
    pub fn is_default(&self) -> bool {
        matches!(self.mode, EnvironmentNetworkMode::AllowAll) && self.allow.is_empty()
    }
}

#[derive(
    Debug,
    Clone,
    Copy,
    PartialEq,
    Eq,
    Serialize,
    Deserialize,
    strum::Display,
    strum::EnumString,
    strum::IntoStaticStr,
)]
#[serde(rename_all = "snake_case")]
#[strum(serialize_all = "snake_case")]
pub enum EnvironmentNetworkMode {
    AllowAll,
    Block,
    CidrAllowList,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct EnvironmentLifecycleSettings {
    pub preserve:         bool,
    pub stop_on_terminal: bool,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub auto_stop:        Option<Duration>,
}

impl Default for EnvironmentLifecycleSettings {
    fn default() -> Self {
        Self {
            preserve:         false,
            stop_on_terminal: true,
            auto_stop:        None,
        }
    }
}

impl EnvironmentLifecycleSettings {
    #[must_use]
    pub fn is_default(&self) -> bool {
        !self.preserve && self.stop_on_terminal && self.auto_stop.is_none()
    }
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct EnvironmentVolumeSettings {
    pub id:         String,
    pub mount_path: String,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub subpath:    Option<String>,
}

/// Resolved `[run.environment]` selection plus selected environment.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct RunEnvironmentSettings {
    /// Slug of the selected environment in the workflow's environment
    /// catalog. Always populated for resolved runs.
    pub id:          String,
    /// The fully resolved, overlay-applied environment for the run.
    #[serde(flatten)]
    pub environment: EnvironmentSettings,
}

impl Default for RunEnvironmentSettings {
    fn default() -> Self {
        Self {
            id:          "default".to_string(),
            environment: EnvironmentSettings::default(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn environment_provider_round_trips_via_strum() {
        assert_eq!(EnvironmentProvider::Docker.to_string(), "docker");
        assert_eq!(
            "daytona".parse::<EnvironmentProvider>().unwrap(),
            EnvironmentProvider::Daytona
        );
    }

    #[test]
    fn network_mode_serializes_snake_case() {
        let mode = EnvironmentNetworkMode::CidrAllowList;
        let json = serde_json::to_string(&mode).unwrap();
        assert_eq!(json, "\"cidr_allow_list\"");
    }

    #[test]
    fn lifecycle_defaults_match_plan() {
        let lifecycle = EnvironmentLifecycleSettings::default();
        assert!(!lifecycle.preserve);
        assert!(lifecycle.stop_on_terminal);
        assert!(lifecycle.auto_stop.is_none());
    }

    #[test]
    fn environment_settings_default_uses_local_provider() {
        let env = EnvironmentSettings::default();
        assert_eq!(env.provider, EnvironmentProvider::Local);
    }
}
