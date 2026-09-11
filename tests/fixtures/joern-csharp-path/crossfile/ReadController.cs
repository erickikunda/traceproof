using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class ReadController : ControllerBase {
 [HttpGet]
 public string Read([FromQuery] string term) {
    return Reader.Read(term);
 }
}
}
