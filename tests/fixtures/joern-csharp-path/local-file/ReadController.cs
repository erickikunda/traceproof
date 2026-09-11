using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class ReadController : ControllerBase {
 [HttpGet]
 public string Read([FromQuery] string term) {
    return System.IO.File.ReadAllText("/srv/files/" + term);
 }
}
}

namespace System.IO { public static class File {
 public static string ReadAllText(string path) { return path; }
} }
