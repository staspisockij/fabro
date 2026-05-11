use agent_client_protocol::schema::{
    ContentBlock, ContentChunk, SessionNotification, SessionUpdate,
};
use serde_json::json;

pub const SESSION_ID: &str = "sess-1";

pub fn agent_message_chunk(session_id: &str, text: &str) -> SessionNotification {
    SessionNotification::new(
        session_id.to_string(),
        SessionUpdate::AgentMessageChunk(ContentChunk::new(ContentBlock::from(text.to_string()))),
    )
}

pub fn agent_message_chunk_json(session_id: &str, text: &str) -> serde_json::Value {
    json!({
        "jsonrpc": "2.0",
        "method": "session/update",
        "params": agent_message_chunk(session_id, text),
    })
}

pub fn fake_acp_agent_script() -> &'static str {
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
        for text in ["hello ", "from acp"]:
            send({
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "sessionId": session_id,
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": text}
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
