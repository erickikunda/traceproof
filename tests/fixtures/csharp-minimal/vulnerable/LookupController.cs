using System.Data.Common;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Mvc;

public static class Routes {
    public static void Register(WebApplication app) {
        app.MapGet("/users", ([FromQuery] string name, [FromServices] DbConnection connection) => {
        var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM users WHERE name='" + name + "'";
        return command.ExecuteReader();
        });
    }
}
