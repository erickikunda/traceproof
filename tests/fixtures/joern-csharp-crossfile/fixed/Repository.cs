using System.Data.Common;
public class SearchRepository {
  public static DbDataReader Find(string term, DbConnection connection) {
    var command = connection.CreateCommand();
    command.CommandText = "SELECT * FROM users WHERE name=@name";
    var parameter = command.CreateParameter();
    parameter.ParameterName = "@name";
    parameter.Value = term;
    command.Parameters.Add(parameter);
    return command.ExecuteReader();
  }
}
