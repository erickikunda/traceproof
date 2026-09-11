use std::process::Command;
fn lookup(input: String) {
    Command::new("sh").arg("-c").arg(input).output().unwrap();
}
fn main() { lookup(std::env::args().nth(1).unwrap()); }
