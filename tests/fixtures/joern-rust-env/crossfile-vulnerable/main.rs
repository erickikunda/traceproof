mod service;
mod repository;
fn main() {
 let value = std::env::var("TRACEPROOF_COMMAND").unwrap();
 service::dispatch(value);
}
