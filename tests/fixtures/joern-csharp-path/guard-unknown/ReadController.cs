using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class ReadController : ControllerBase {
 [HttpGet]
 public string Read([FromQuery] string term) {
    if (term.Contains("..")) throw new System.Exception();
    return System.IO.File.ReadAllText("/srv/files/" + term);
 }
}
}
