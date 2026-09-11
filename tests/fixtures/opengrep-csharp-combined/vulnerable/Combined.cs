using Microsoft.AspNetCore.Mvc;
using System.Data.Common;
public class SearchController : ControllerBase {
  [HttpGet]
  public DbDataReader Lookup([FromQuery] string name, DbConnection connection) {
    return SearchService.Find(name, connection);
  }
}
public class SearchRepository {
  public static DbDataReader Find(string term, DbConnection connection) {
    var command = connection.CreateCommand();
    command.CommandText = "SELECT * FROM users WHERE name='" + term + "'";
    return command.ExecuteReader();
  }
}
public class SearchService {
  public static DbDataReader Find(string term, DbConnection connection) {
    return SearchRepository.Find(term, connection);
  }
}
