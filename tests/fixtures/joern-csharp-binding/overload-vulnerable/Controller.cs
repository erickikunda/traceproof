using System.Data.Common;
public class Controller {
  public DbDataReader Lookup(string name, DbConnection connection) {
    return Worker.Find(name, connection);
  }
}
