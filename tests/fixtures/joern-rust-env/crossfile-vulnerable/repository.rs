pub fn execute(value: String) {
 std::process::Command::new("sh").arg("-c").arg(value).status();
}
