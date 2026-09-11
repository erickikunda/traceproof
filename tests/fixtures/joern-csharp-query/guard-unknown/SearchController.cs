using System.Data.Common;
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("users")]
public class SearchController : ControllerBase {
    private readonly DbConnection connection;
    public SearchController(DbConnection connection) { this.connection = connection; }

    [HttpGet]
    public DbDataReader Search([FromQuery] string term) {
        if (term.Length > 30) throw new System.Exception();
        var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM users WHERE term='" + term + "'";
        return command.ExecuteReader();
    }
}
