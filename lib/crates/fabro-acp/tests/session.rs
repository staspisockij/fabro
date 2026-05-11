use std::collections::HashMap;
use std::sync::Arc;

use agent_client_protocol::schema::StopReason;
use fabro_acp::{AcpError, AcpRunRequest, resolve_acp_command, run_acp_turn};
use fabro_model::Provider;
use fabro_sandbox::{LocalSandbox, Sandbox, shell_quote};
use tokio_util::sync::CancellationToken;

#[tokio::test]
async fn session_lifecycle_initializes_sends_prompt_and_aggregates_text() {
    let tempdir = tempfile::tempdir().unwrap();
    let script_path = tempdir.path().join("fake_acp_agent.py");
    let record_path = tempdir.path().join("methods.txt");
    tokio::fs::write(&script_path, fake_agent_script())
        .await
        .unwrap();

    let raw_command = format!("python3 {}", shell_quote(&script_path.to_string_lossy()));
    let command = resolve_acp_command(Provider::OpenAi, Some(&raw_command)).unwrap();
    let sandbox: Arc<dyn Sandbox> = Arc::new(LocalSandbox::new(tempdir.path().to_path_buf()));

    let result = run_acp_turn(AcpRunRequest {
        command,
        prompt: "hello".to_string(),
        cwd: tempdir.path().to_string_lossy().into_owned(),
        timeout_ms: Some(5_000),
        env: HashMap::from([(
            "ACP_RECORD".to_string(),
            record_path.to_string_lossy().into_owned(),
        )]),
        sandbox,
        cancel_token: CancellationToken::new(),
        on_activity: None,
    })
    .await
    .unwrap();

    assert_eq!(result.text, "hello from acp");
    assert_eq!(result.stop_reason, StopReason::EndTurn);
    assert_eq!(
        tokio::fs::read_to_string(record_path).await.unwrap(),
        "initialize\nsession/new\nsession/prompt\n"
    );
}

#[tokio::test]
async fn permission_request_selects_allow_always() {
    let tempdir = tempfile::tempdir().unwrap();
    let permission_path = tempdir.path().join("permission.json");

    let result = run_fake_agent(
        tempdir.path(),
        HashMap::from([
            ("ACP_MODE".to_string(), "permission".to_string()),
            (
                "ACP_PERMISSION".to_string(),
                permission_path.to_string_lossy().into_owned(),
            ),
        ]),
        Some(5_000),
        CancellationToken::new(),
    )
    .await
    .unwrap();

    assert_eq!(result.text, "hello from acp");
    let permission = tokio::fs::read_to_string(permission_path).await.unwrap();
    assert!(permission.contains(r#""outcome":"selected""#));
    assert!(permission.contains(r#""optionId":"always""#));
}

#[tokio::test]
async fn runs_inside_sandbox_and_uses_requested_cwd() {
    let tempdir = tempfile::tempdir().unwrap();
    let cwd_path = tempdir.path().join("session_new.json");

    let result = run_fake_agent(
        tempdir.path(),
        HashMap::from([
            ("ACP_MODE".to_string(), "write_file".to_string()),
            (
                "ACP_SESSION_NEW_PARAMS".to_string(),
                cwd_path.to_string_lossy().into_owned(),
            ),
        ]),
        Some(5_000),
        CancellationToken::new(),
    )
    .await
    .unwrap();

    assert_eq!(result.text, "hello from acp");
    assert_eq!(
        tokio::fs::read_to_string(tempdir.path().join("hello.txt"))
            .await
            .unwrap(),
        "hello from sandbox\n"
    );
    assert!(
        tokio::fs::read_to_string(cwd_path)
            .await
            .unwrap()
            .contains(&tempdir.path().to_string_lossy().into_owned())
    );
}

#[tokio::test]
async fn cancellation_sends_session_cancel_and_returns_cancelled() {
    let tempdir = tempfile::tempdir().unwrap();
    let cancel_path = tempdir.path().join("cancel.txt");
    let cancel_token = CancellationToken::new();
    let cancel_for_task = cancel_token.clone();

    let task = tokio::spawn(async move {
        run_fake_agent(
            tempdir.path(),
            HashMap::from([
                ("ACP_MODE".to_string(), "cancel".to_string()),
                (
                    "ACP_CANCEL_RECORD".to_string(),
                    cancel_path.to_string_lossy().into_owned(),
                ),
            ]),
            Some(5_000),
            cancel_for_task,
        )
        .await
    });

    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    cancel_token.cancel();
    let err = task.await.unwrap().unwrap_err();

    assert!(matches!(err, AcpError::Cancelled));
}

#[tokio::test]
async fn refusal_stop_reason_returns_text() {
    let tempdir = tempfile::tempdir().unwrap();

    let result = run_fake_agent(
        tempdir.path(),
        HashMap::from([("ACP_STOP_REASON".to_string(), "refusal".to_string())]),
        Some(5_000),
        CancellationToken::new(),
    )
    .await
    .unwrap();

    assert_eq!(result.text, "hello from acp");
    assert_eq!(result.stop_reason, StopReason::Refusal);
}

#[tokio::test]
async fn max_tokens_stop_reason_returns_partial_text_error() {
    let tempdir = tempfile::tempdir().unwrap();

    let err = run_fake_agent(
        tempdir.path(),
        HashMap::from([("ACP_STOP_REASON".to_string(), "max_tokens".to_string())]),
        Some(5_000),
        CancellationToken::new(),
    )
    .await
    .unwrap_err();

    let AcpError::StopReason { stop_reason, text } = err else {
        panic!("expected stop reason error");
    };
    assert_eq!(stop_reason, "max_tokens");
    assert_eq!(text, "hello from acp");
}

#[tokio::test]
async fn max_turn_requests_stop_reason_returns_partial_text_error() {
    let tempdir = tempfile::tempdir().unwrap();

    let err = run_fake_agent(
        tempdir.path(),
        HashMap::from([(
            "ACP_STOP_REASON".to_string(),
            "max_turn_requests".to_string(),
        )]),
        Some(5_000),
        CancellationToken::new(),
    )
    .await
    .unwrap_err();

    let AcpError::StopReason { stop_reason, text } = err else {
        panic!("expected stop reason error");
    };
    assert_eq!(stop_reason, "max_turn_requests");
    assert_eq!(text, "hello from acp");
}

#[tokio::test]
async fn timeout_terminates_process_and_returns_timeout() {
    let tempdir = tempfile::tempdir().unwrap();

    let err = run_fake_agent(
        tempdir.path(),
        HashMap::from([("ACP_MODE".to_string(), "timeout".to_string())]),
        Some(100),
        CancellationToken::new(),
    )
    .await
    .unwrap_err();

    assert!(matches!(err, AcpError::TimedOut { .. }));
}

#[tokio::test]
async fn malformed_json_returns_protocol_error() {
    let tempdir = tempfile::tempdir().unwrap();

    let err = run_fake_agent(
        tempdir.path(),
        HashMap::from([("ACP_MODE".to_string(), "malformed".to_string())]),
        Some(5_000),
        CancellationToken::new(),
    )
    .await
    .unwrap_err();

    assert!(matches!(err, AcpError::Protocol(_)));
}

#[tokio::test]
async fn early_exit_returns_protocol_error_with_stderr() {
    let tempdir = tempfile::tempdir().unwrap();

    let err = run_fake_agent(
        tempdir.path(),
        HashMap::from([("ACP_MODE".to_string(), "early_exit".to_string())]),
        Some(5_000),
        CancellationToken::new(),
    )
    .await
    .unwrap_err();

    assert!(matches!(err, AcpError::Protocol(_)));
}

async fn run_fake_agent(
    tempdir: &std::path::Path,
    env: HashMap<String, String>,
    timeout_ms: Option<u64>,
    cancel_token: CancellationToken,
) -> Result<fabro_acp::AcpRunResult, AcpError> {
    let script_path = tempdir.join("fake_acp_agent.py");
    tokio::fs::write(&script_path, fake_agent_script())
        .await
        .unwrap();
    let raw_command = format!("python3 {}", shell_quote(&script_path.to_string_lossy()));
    let command = resolve_acp_command(Provider::OpenAi, Some(&raw_command)).unwrap();
    let sandbox: Arc<dyn Sandbox> = Arc::new(LocalSandbox::new(tempdir.to_path_buf()));

    run_acp_turn(AcpRunRequest {
        command,
        prompt: "hello".to_string(),
        cwd: tempdir.to_string_lossy().into_owned(),
        timeout_ms,
        env,
        sandbox,
        cancel_token,
        on_activity: None,
    })
    .await
}

fn fake_agent_script() -> &'static str {
    r#"
import json
import os
import sys
import time

methods = []
session_id = "sess-1"

def send(message):
    print(json.dumps(message), flush=True)

def respond(message, result):
    send({"jsonrpc": "2.0", "id": message["id"], "result": result})

for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    methods.append(method)

    if method == "initialize":
        respond(message, {"protocolVersion": 1, "agentCapabilities": {}})
    elif method == "session/new":
        if os.environ.get("ACP_SESSION_NEW_PARAMS"):
            with open(os.environ["ACP_SESSION_NEW_PARAMS"], "w", encoding="utf-8") as record:
                record.write(json.dumps(message.get("params", {}), separators=(",", ":")))
        respond(message, {"sessionId": session_id})
    elif method == "session/prompt":
        mode = os.environ.get("ACP_MODE", "normal")
        if mode == "timeout":
            time.sleep(60)
        if mode == "malformed":
            print("malformed json", file=sys.stderr, flush=True)
            print("{not-json", flush=True)
            break
        if mode == "early_exit":
            print("early boom", file=sys.stderr, flush=True)
            sys.exit(2)
        if mode == "write_file":
            with open("hello.txt", "w", encoding="utf-8") as file:
                file.write("hello from sandbox\n")
        if mode == "cancel":
            for cancel_line in sys.stdin:
                cancel_message = json.loads(cancel_line)
                if cancel_message.get("method") == "session/cancel":
                    with open(os.environ["ACP_CANCEL_RECORD"], "w", encoding="utf-8") as record:
                        record.write("session/cancel\n")
                    respond(message, {"stopReason": "cancelled"})
                    sys.exit(0)
        if mode == "permission":
            send({
                "jsonrpc": "2.0",
                "id": "permission-1",
                "method": "session/request_permission",
                "params": {
                    "sessionId": session_id,
                    "toolCall": {"toolCallId": "tool-1"},
                    "options": [
                        {"optionId": "reject", "name": "Reject", "kind": "reject_once"},
                        {"optionId": "once", "name": "Allow once", "kind": "allow_once"},
                        {"optionId": "always", "name": "Allow always", "kind": "allow_always"}
                    ]
                }
            })
            permission_response = json.loads(sys.stdin.readline())
            with open(os.environ["ACP_PERMISSION"], "w", encoding="utf-8") as permission:
                permission.write(json.dumps(permission_response.get("result", {}), separators=(",", ":")))
        send({
            "jsonrpc": "2.0",
            "method": "session/update",
            "params": {
                "sessionId": session_id,
                "update": {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "hello "}
                }
            }
        })
        send({
            "jsonrpc": "2.0",
            "method": "session/update",
            "params": {
                "sessionId": session_id,
                "update": {
                    "sessionUpdate": "agent_message_chunk",
                    "content": {"type": "text", "text": "from acp"}
                }
            }
        })
        respond(message, {"stopReason": os.environ.get("ACP_STOP_REASON", "end_turn")})
        if os.environ.get("ACP_RECORD"):
            with open(os.environ["ACP_RECORD"], "w", encoding="utf-8") as record:
                record.write("\n".join(methods) + "\n")
        break
    else:
        send({
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "error": {"code": -32601, "message": "method not found"}
        })
"#
}
