use crate::{
    AuthMethod, IdpIdentity, Principal, RunClientProvenance, RunProvenance, RunServerProvenance,
};

#[must_use]
pub fn test_principal() -> Principal {
    Principal::user(
        IdpIdentity::new("fabro:test", "test-user").expect("test identity should be valid"),
        "test".to_string(),
        AuthMethod::DevToken,
    )
}

#[must_use]
pub fn test_run_provenance() -> RunProvenance {
    RunProvenance {
        server:  Some(RunServerProvenance {
            version: "test".to_string(),
        }),
        client:  Some(RunClientProvenance {
            user_agent: Some("fabro-test/0.0.0".to_string()),
            name:       Some("fabro-test".to_string()),
            version:    Some("0.0.0".to_string()),
        }),
        subject: test_principal(),
    }
}
