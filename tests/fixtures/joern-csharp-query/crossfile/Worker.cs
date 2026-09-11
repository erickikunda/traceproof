using System.Data.Common;
namespace Demo { public static class Worker {
 public static DbDataReader Run(DbConnection connection, string value) {
  var command = connection.CreateCommand();
  command.CommandText = "SELECT * FROM users WHERE term='" + value + "'";
  return command.ExecuteReader();
 }
} }
