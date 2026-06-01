use crate::{AuthMethod, IdpIdentity, Principal, RunProvenance};

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
    test_run_provenance_with(test_principal())
}

#[must_use]
pub fn test_run_provenance_with(subject: Principal) -> RunProvenance {
    RunProvenance {
        server: None,
        client: None,
        subject,
    }
}
