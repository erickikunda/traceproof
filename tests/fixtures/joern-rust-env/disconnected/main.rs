fn main() {
    let command = std::env::var("TRACEPROOF_COMMAND").unwrap();
}
fn unrelated(command: String) {
    std::process::Command::new("sh").arg("-c").arg(command).status();
}
