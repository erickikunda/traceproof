using System.Data.Common;
namespace Danger {
public class Repository {
 public static DbDataReader Find(string term, DbConnection connection) {
  var command = connection.CreateCommand();
  command.CommandText = "SELECT " + term;
  return command.ExecuteReader();
 }
}
}
