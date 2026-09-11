mod service;
mod repository;
fn lookup(input: String) { service::run(input); }
fn main() { lookup(std::env::args().nth(1).unwrap()); }
