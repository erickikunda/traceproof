fn main() {
    let command = std::env::var("TRACEPROOF_COMMAND").unwrap();
    std::process::Command::new("printf").arg("%s").arg(command).status();
}
