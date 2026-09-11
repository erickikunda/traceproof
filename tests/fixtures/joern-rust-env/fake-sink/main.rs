mod fake {
 pub struct Command;
 impl Command {
  pub fn new(_: &str) -> Self { Self }
  pub fn arg<T>(self, _: T) -> Self { self }
  pub fn status(self) {}
 }
}
fn main() {
    let command = std::env::var("TRACEPROOF_COMMAND").unwrap();
    fake::Command::new("sh").arg("-c").arg(command).status();
}
