using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class RunController : ControllerBase {
 [HttpGet]
 public object Run([FromQuery] string term) {
    if (term.Length > 30) throw new System.Exception();
    return System.Diagnostics.Process.Start("/bin/sh", "-c \"" + term + "\"");
 }
}
}
