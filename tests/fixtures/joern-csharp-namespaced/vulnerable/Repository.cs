using System.Data.Common;
namespace TraceProofProbe {
public class SearchRepository {
  public static DbDataReader Find(string term, DbConnection connection) {
    var command = connection.CreateCommand();
    command.CommandText = "SELECT * FROM users WHERE name='" + term + "'";
    return command.ExecuteReader();
  }
}
}
