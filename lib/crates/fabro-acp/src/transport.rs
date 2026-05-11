use std::{collections::HashMap, pin::Pin, sync::Arc};

use agent_client_protocol::{Client, ConnectTo, Lines};
use fabro_sandbox::{Sandbox, StderrCollector, StdioProcessHandle};
use futures::{AsyncBufReadExt, AsyncWriteExt};
use tokio_util::compat::{TokioAsyncReadCompatExt, TokioAsyncWriteCompatExt};
use tokio_util::sync::CancellationToken;

use crate::command::AcpCommand;

#[derive(Clone)]
pub(crate) struct TransportState {
    handle: Arc<tokio::sync::Mutex<Option<StdioProcessHandle>>>,
    stderr: Arc<tokio::sync::Mutex<Option<StderrCollector>>>,
}

impl TransportState {
    pub(crate) fn new() -> Self {
        Self {
            handle: Arc::new(tokio::sync::Mutex::new(None)),
            stderr: Arc::new(tokio::sync::Mutex::new(None)),
        }
    }

    async fn set_process(&self, handle: StdioProcessHandle, stderr: StderrCollector) {
        *self.handle.lock().await = Some(handle);
        *self.stderr.lock().await = Some(stderr);
    }

    pub(crate) async fn terminate(&self) -> fabro_sandbox::Result<()> {
        if let Some(handle) = self.handle.lock().await.as_ref().cloned() {
            handle.terminate().await?;
        }
        Ok(())
    }

    pub(crate) async fn stderr_tail(&self) -> String {
        if let Some(stderr) = self.stderr.lock().await.as_ref().cloned() {
            return stderr.tail_string().await;
        }
        String::new()
    }
}

pub(crate) struct SandboxAcpTransport {
    command: AcpCommand,
    cwd: String,
    env: HashMap<String, String>,
    sandbox: Arc<dyn Sandbox>,
    cancel_token: CancellationToken,
    state: TransportState,
}

impl SandboxAcpTransport {
    pub(crate) fn new(
        command: AcpCommand,
        cwd: String,
        env: HashMap<String, String>,
        sandbox: Arc<dyn Sandbox>,
        cancel_token: CancellationToken,
        state: TransportState,
    ) -> Self {
        Self {
            command,
            cwd,
            env,
            sandbox,
            cancel_token,
            state,
        }
    }
}

impl ConnectTo<Client> for SandboxAcpTransport {
    async fn connect_to(
        self,
        client: impl ConnectTo<agent_client_protocol::Agent>,
    ) -> agent_client_protocol::Result<()> {
        let mut env = self.command.env().clone();
        env.extend(self.env);

        let process = self
            .sandbox
            .spawn_stdio_process(
                &self.command.to_shell_command(),
                Some(&self.cwd),
                Some(&env),
                Some(self.cancel_token),
            )
            .await
            .map_err(agent_client_protocol::Error::into_internal_error)?;

        let handle = process.handle.clone();
        let stderr = process.stderr.clone();
        self.state.set_process(handle.clone(), stderr.clone()).await;

        let incoming_lines = Box::pin(futures::io::BufReader::new(process.stdout.compat()).lines())
            as Pin<Box<dyn futures::Stream<Item = std::io::Result<String>> + Send>>;
        let outgoing_sink = Box::pin(futures::sink::unfold(
            process.stdin.compat_write(),
            async move |mut writer, line: String| {
                let mut bytes = line.into_bytes();
                bytes.push(b'\n');
                writer.write_all(&bytes).await?;
                Ok::<_, std::io::Error>(writer)
            },
        ));

        let protocol =
            agent_client_protocol::ConnectTo::<Client>::connect_to(Lines::new(outgoing_sink, incoming_lines), client);
        tokio::select! {
            result = protocol => {
                let _ = tokio::time::timeout(std::time::Duration::from_millis(500), handle.wait()).await;
                result
            }
            termination = handle.wait() => {
                let termination = termination.map_err(agent_client_protocol::Error::into_internal_error)?;
                let stderr = stderr.tail_string().await;
                Err(agent_client_protocol::util::internal_error(format!(
                    "ACP process exited before protocol completed: termination={termination:?}, stderr={stderr}"
                )))
            }
        }
    }
}
