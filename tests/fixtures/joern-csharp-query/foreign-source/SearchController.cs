using System.Data.Common;
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("users")]
public class SearchController : ControllerBase {
    private readonly DbConnection connection;
    public SearchController(DbConnection connection) { this.connection = connection; }

    [HttpGet]
    public DbDataReader Search([Other] string term) {
        var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM users WHERE term='" + term + "'";
        return command.ExecuteReader();
    }
}

class OtherAttribute : System.Attribute {}
