use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;

use agent_client_protocol::schema::{
    CancelNotification, ContentBlock, ContentChunk, InitializeRequest, PermissionOptionKind,
    ProtocolVersion, RequestPermissionOutcome, RequestPermissionRequest, RequestPermissionResponse,
    SelectedPermissionOutcome, SessionNotification, SessionUpdate, StopReason,
};
use agent_client_protocol::util::{MatchDispatch, internal_error};
use agent_client_protocol::{ActiveSession, Agent, Client, Error as ProtocolError, SessionMessage};
use fabro_sandbox::Sandbox;
use fabro_util::time::elapsed_ms;
use tokio::time::{sleep, timeout};
use tokio_util::sync::CancellationToken;

use crate::command::AcpCommand;
use crate::error::AcpError;
use crate::transport::{SandboxAcpTransport, TransportState};

pub struct AcpRunRequest {
    pub command:      AcpCommand,
    pub prompt:       String,
    pub cwd:          String,
    pub timeout_ms:   Option<u64>,
    pub env:          HashMap<String, String>,
    pub sandbox:      Arc<dyn Sandbox>,
    pub cancel_token: CancellationToken,
    pub on_activity:  Option<Arc<dyn Fn() + Send + Sync>>,
}

#[derive(Debug)]
pub struct AcpRunResult {
    pub text:        String,
    pub stop_reason: StopReason,
    pub stderr:      String,
    pub duration_ms: u64,
}

pub async fn run_acp_turn(request: AcpRunRequest) -> Result<AcpRunResult, AcpError> {
    let start = std::time::Instant::now();
    let state = TransportState::new();
    let cancel_token = request.cancel_token.clone();
    let run_cancel_token = request.cancel_token.clone();
    let permission_cancel_token = request.cancel_token.clone();
    let prompt = request.prompt.clone();
    let cwd = request.cwd.clone();
    let on_activity = request.on_activity.clone();
    let state_for_run = state.clone();
    let transport = SandboxAcpTransport::new(
        request.command,
        request.cwd,
        request.env,
        request.sandbox,
        request.cancel_token.clone(),
        state.clone(),
    );

    let run = Client
        .builder()
        .name("fabro")
        .on_receive_request(
            async move |request: RequestPermissionRequest, responder, _connection| {
                let outcome = if permission_cancel_token.is_cancelled() {
                    RequestPermissionOutcome::Cancelled
                } else {
                    select_permission_outcome(&request)
                };
                responder.respond(RequestPermissionResponse::new(outcome))
            },
            agent_client_protocol::on_receive_request!(),
        )
        .connect_with(transport, async move |cx| {
            cx.send_request(InitializeRequest::new(ProtocolVersion::V1))
                .block_task()
                .await?;

            cx.build_session(&cwd)
                .block_task()
                .run_until(async |mut session| {
                    session.send_prompt(prompt)?;
                    read_turn(
                        &mut session,
                        &cancel_token,
                        on_activity.as_ref(),
                        &state_for_run,
                    )
                    .await
                })
                .await
        });

    let outcome = match request.timeout_ms {
        Some(timeout_ms) => {
            if let Ok(result) = timeout(Duration::from_millis(timeout_ms), run).await {
                result
            } else {
                state.terminate().await?;
                if run_cancel_token.is_cancelled() {
                    return Err(AcpError::Cancelled);
                }
                return Err(AcpError::TimedOut {
                    stderr: state.stderr_tail().await,
                });
            }
        }
        None => run.await,
    };
    let (text, stop_reason) = match outcome {
        Ok(result) => result,
        Err(_) if run_cancel_token.is_cancelled() => {
            state.terminate().await?;
            return Err(AcpError::Cancelled);
        }
        Err(error) => {
            state.terminate().await?;
            return Err(map_protocol_error(error));
        }
    };

    state.terminate().await?;
    let stderr = state.stderr_tail().await;
    Ok(AcpRunResult {
        text,
        stop_reason,
        stderr,
        duration_ms: elapsed_ms(start),
    })
}

fn map_protocol_error(error: ProtocolError) -> AcpError {
    let message = error.to_string();
    if message.contains("ACP turn was cancelled") {
        AcpError::Cancelled
    } else if let Some(rest) = message.split("ACP prompt stopped with ").nth(1) {
        let (stop_reason, text) = rest
            .split_once(": ")
            .map_or((rest, ""), |(stop_reason, text)| (stop_reason, text));
        AcpError::StopReason {
            stop_reason: stop_reason.to_string(),
            text:        text.trim_end_matches('"').to_string(),
        }
    } else {
        AcpError::Protocol(error)
    }
}

fn select_permission_outcome(request: &RequestPermissionRequest) -> RequestPermissionOutcome {
    let selected = request
        .options
        .iter()
        .find(|option| option.kind == PermissionOptionKind::AllowAlways)
        .or_else(|| {
            request
                .options
                .iter()
                .find(|option| option.kind == PermissionOptionKind::AllowOnce)
        })
        .or_else(|| {
            request.options.iter().find(|option| {
                !matches!(
                    option.kind,
                    PermissionOptionKind::RejectOnce | PermissionOptionKind::RejectAlways
                )
            })
        });

    selected.map_or(RequestPermissionOutcome::Cancelled, |option| {
        RequestPermissionOutcome::Selected(SelectedPermissionOutcome::new(option.option_id.clone()))
    })
}

async fn read_turn(
    session: &mut ActiveSession<'_, Agent>,
    cancel_token: &CancellationToken,
    on_activity: Option<&Arc<dyn Fn() + Send + Sync>>,
    state: &TransportState,
) -> Result<(String, StopReason), ProtocolError> {
    let mut text = String::new();
    let mut cancel_sent = false;

    loop {
        tokio::select! {
            update = session.read_update() => {
                if let Some(on_activity) = on_activity {
                    on_activity();
                }
                match update? {
                    SessionMessage::SessionMessage(dispatch) => {
                        MatchDispatch::new(dispatch)
                            .if_notification(async |notification: SessionNotification| {
                                if let SessionUpdate::AgentMessageChunk(ContentChunk {
                                    content: ContentBlock::Text(text_chunk),
                                    ..
                                }) = notification.update {
                                    text.push_str(&text_chunk.text);
                                }
                                Ok(())
                            })
                            .await
                            .otherwise_ignore()?;
                    }
                    SessionMessage::StopReason(stop_reason) => {
                        return match stop_reason {
                            StopReason::EndTurn | StopReason::Refusal => Ok((text, stop_reason)),
                            StopReason::Cancelled => {
                                Err(internal_error("ACP turn was cancelled"))
                            }
                            StopReason::MaxTokens | StopReason::MaxTurnRequests => {
                                Err(internal_error(format!(
                                    "ACP prompt stopped with {}: {text}",
                                    stop_reason_name(stop_reason)
                                )))
                            }
                            _ => Err(internal_error(format!(
                                "ACP prompt stopped with {}: {text}",
                                stop_reason_name(stop_reason)
                            ))),
                        };
                    }
                    _ => {}
                }
            }
            () = cancel_token.cancelled(), if !cancel_sent => {
                cancel_sent = true;
                session.connection().send_notification_to(
                    Agent,
                    CancelNotification::new(session.session_id().clone()),
                )?;
            }
            () = sleep(Duration::from_millis(500)), if cancel_sent => {
                state.terminate().await.map_err(ProtocolError::into_internal_error)?;
                return Err(internal_error("ACP turn was cancelled"));
            }
        }
    }
}

fn stop_reason_name(stop_reason: StopReason) -> &'static str {
    match stop_reason {
        StopReason::EndTurn => "end_turn",
        StopReason::MaxTokens => "max_tokens",
        StopReason::MaxTurnRequests => "max_turn_requests",
        StopReason::Refusal => "refusal",
        StopReason::Cancelled => "cancelled",
        _ => "unknown",
    }
}
