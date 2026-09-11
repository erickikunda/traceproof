use std::process::Command;
pub fn execute(value: String) {
    Command::new("sh").arg("-c").arg("printf safe").output().unwrap();
}
