using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class ReadController : ControllerBase {
 [HttpGet]
 public string Read([FromQuery] string term) {
    return System.IO.File.ReadAllText("/srv/files/fixed.txt");
 }
}
}
