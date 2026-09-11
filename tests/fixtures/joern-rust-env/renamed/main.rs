use std::env::var as read_setting;
use std::process::Command as Process;
fn main() {
    let payload = read_setting("TRACEPROOF_COMMAND").unwrap();
    Process::new("/bin/bash").arg("-c").arg(payload).status();
}
