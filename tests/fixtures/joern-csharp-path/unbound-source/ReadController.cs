using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class ReadController : ControllerBase {
 [HttpGet]
 public string Read(string term) {
    return System.IO.File.ReadAllText("/srv/files/" + term);
 }
}
}
