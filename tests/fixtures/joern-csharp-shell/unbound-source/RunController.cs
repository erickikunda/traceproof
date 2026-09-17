using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class RunController : ControllerBase {
 [HttpGet]
 public object Run(string term) {
    return System.Diagnostics.Process.Start("/bin/sh", "-c \"" + term + "\"");
 }
}
}
