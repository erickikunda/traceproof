using System.Data.Common;
using System.Web.Mvc;

[RoutePrefix("users")]
public class LookupController : Controller {
    private readonly DbConnection connection;
    public LookupController(DbConnection connection) { this.connection = connection; }

    [HttpGet]
    [Route("")]
    public DbDataReader Lookup(string name) {
        var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM users WHERE name=@name";
        var parameter = command.CreateParameter();
        parameter.ParameterName = "@name";
        parameter.Value = name;
        command.Parameters.Add(parameter);
        return command.ExecuteReader();
    }
}
