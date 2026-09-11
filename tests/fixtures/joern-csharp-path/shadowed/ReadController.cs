using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class ReadController : ControllerBase {
 [HttpGet]
 public string Read([FromQuery] string term) {
    return Other.ReadAllText(term);
 }
}
public static class Other { public static string ReadAllText(string value) { return value; } }
}
