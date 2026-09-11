use std::process::Command;
fn lookup(input: String) {
    Command::new("sh").arg("-c").arg("printf safe").output().unwrap();
    println!("{}", input);
}
fn main() { lookup(std::env::args().nth(1).unwrap()); }
