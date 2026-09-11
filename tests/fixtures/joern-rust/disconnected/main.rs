use std::process::Command;
fn lookup(input: String) { println!("{}", input); }
fn detached(other: String) {
    Command::new("sh").arg("-c").arg(other).output().unwrap();
}
fn main() { lookup(std::env::args().nth(1).unwrap()); }
