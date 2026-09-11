using Microsoft.AspNetCore.Mvc;
using System.Data.Common;
namespace TraceProofProbe {
public class SearchController : ControllerBase {
  [HttpGet]
  public DbDataReader Lookup([FromQuery] string name, DbConnection connection) {
    return SearchService.Find(name, connection);
  }
}
}
