using System.Data.Common;
public class Worker {
  public static DbDataReader Find(string term, DbConnection connection) {
    var command = connection.CreateCommand();
    command.CommandText = "SELECT " + term;
    return command.ExecuteReader();
  }
  public static DbDataReader Find(int term, DbConnection connection) {
    return null;
  }
}
