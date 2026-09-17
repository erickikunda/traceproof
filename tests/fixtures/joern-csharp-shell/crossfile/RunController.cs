using Microsoft.AspNetCore.Mvc;
namespace Demo {
public class RunController : ControllerBase {
 [HttpGet]
 public object Run([FromQuery] string term) {
    return Runner.Run(term);
 }
}
}
