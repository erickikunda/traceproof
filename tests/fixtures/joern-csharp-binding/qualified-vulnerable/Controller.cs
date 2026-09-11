using System.Data.Common;
public class Controller {
  public DbDataReader Lookup(string name, DbConnection connection) {
    return Probe.Worker.Find(name, connection);
  }
}
