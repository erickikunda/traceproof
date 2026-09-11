use std::process::Command;
pub fn execute(value: String) {
    Command::new("sh").arg("-c").arg(value).output().unwrap();
}
