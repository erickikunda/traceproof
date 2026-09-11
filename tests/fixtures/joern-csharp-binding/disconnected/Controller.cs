using System.Data.Common;
public class Controller {
  public DbDataReader Lookup(string name, DbConnection connection) {
    return Safe.Worker.Find(name, connection);
  }
}
