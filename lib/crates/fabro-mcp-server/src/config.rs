use anyhow::Result;
use serde_json::json;

use crate::{McpConfigSettings, McpInitSettings};

pub fn config_json(_settings: McpConfigSettings) -> String {
    serde_json::to_string_pretty(&json!({
        "mcpServers": {
            "fabro": {
                "command": "fabro",
                "args": ["mcp", "start"]
            }
        }
    }))
    .expect("static MCP config should serialize")
        + "\n"
}

pub fn init_agent(_settings: McpInitSettings) -> Result<()> {
    Ok(())
}
