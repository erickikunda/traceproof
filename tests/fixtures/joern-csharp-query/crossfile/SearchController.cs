using System.Data.Common;
using Microsoft.AspNetCore.Mvc;

namespace Demo {
[ApiController]
[Route("users")]
public class SearchController : ControllerBase {
    private readonly DbConnection connection;
    public SearchController(DbConnection connection) { this.connection = connection; }

    [HttpGet]
    public DbDataReader Search([FromQuery] string term) {
        return Worker.Run(connection, term);
    }
}

}
