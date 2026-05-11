use anyhow::{Result, bail};

use crate::McpServerSettings;

pub async fn start(_settings: McpServerSettings) -> Result<()> {
    bail!("fabro mcp start is not implemented yet")
}
