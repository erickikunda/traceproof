using System.Data.Common;
public class Controller {
  private Worker worker = new Worker();
  public DbDataReader Lookup(string name, DbConnection connection) {
    return worker.Find(name, connection);
  }
}
