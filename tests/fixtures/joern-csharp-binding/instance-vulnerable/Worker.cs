using System.Data.Common;
public class Worker {
  public DbDataReader Find(string term, DbConnection connection) {
    var command = connection.CreateCommand();
    command.CommandText = "SELECT " + term;
    return command.ExecuteReader();
  }
}
