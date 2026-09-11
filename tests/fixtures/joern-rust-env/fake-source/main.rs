mod fake { pub fn var(_: &str) -> Result<String, ()> { Ok(String::from("fixed")) } }
fn main() {
    let command = fake::var("TRACEPROOF_COMMAND").unwrap();
    std::process::Command::new("sh").arg("-c").arg(command).status();
}
