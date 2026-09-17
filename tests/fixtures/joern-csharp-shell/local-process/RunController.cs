using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class RunController : ControllerBase {
 [HttpGet]
 public object Run([FromQuery] string term) {
    return System.Diagnostics.Process.Start("/bin/sh", "-c \"" + term + "\"");
 }
}
}
namespace System.Diagnostics { public static class Process { public static object Start(string exe, string args) { return null; } } }
