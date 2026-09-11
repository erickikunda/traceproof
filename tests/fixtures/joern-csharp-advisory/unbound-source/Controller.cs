using System.Data.Common;
using Microsoft.AspNetCore.Mvc;

[ApiController]
[Route("users")]
public class LookupController : ControllerBase {
    private readonly DbConnection connection;
    public LookupController(DbConnection connection) { this.connection = connection; }

    [HttpGet]
    public DbDataReader Lookup(string name) {
        var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM users WHERE name='" + name + "'";
        return command.ExecuteReader();
    }
}
