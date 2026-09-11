fn main() {
    let command = std::env::var("TRACEPROOF_COMMAND").unwrap();
    std::process::Command::new("sh").arg("-c").arg("echo fixed").status();
}
