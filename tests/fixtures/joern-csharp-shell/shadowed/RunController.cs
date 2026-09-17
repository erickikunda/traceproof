using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class RunController : ControllerBase {
 [HttpGet]
 public object Run([FromQuery] string term) {
    return Other.Start("/bin/sh", term);
 }
}
public static class Other { public static object Start(string exe, string args) { return null; } }
}
