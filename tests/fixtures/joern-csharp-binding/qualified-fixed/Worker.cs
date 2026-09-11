using System.Data.Common;
namespace Probe;
public class Worker {
  public static DbDataReader Find(string term, DbConnection connection) {
    var command = connection.CreateCommand();
    command.CommandText = "SELECT 1";
    return command.ExecuteReader();
  }
}
