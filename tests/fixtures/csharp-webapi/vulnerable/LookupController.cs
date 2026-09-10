using System.Data.Common;
using System.Web.Http;

[RoutePrefix("users")]
public class LookupController : ApiController {
    private readonly DbConnection connection;
    public LookupController(DbConnection connection) { this.connection = connection; }

    [HttpGet]
    [Route("")]
    public DbDataReader Lookup([FromUri] string name) {
        var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM users WHERE name='" + name + "'";
        return command.ExecuteReader();
    }
}
