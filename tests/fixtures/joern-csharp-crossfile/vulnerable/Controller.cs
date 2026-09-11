using Microsoft.AspNetCore.Mvc;
using System.Data.Common;
public class SearchController : ControllerBase {
  [HttpGet]
  public DbDataReader Lookup([FromQuery] string name, DbConnection connection) {
    return SearchService.Find(name, connection);
  }
}
