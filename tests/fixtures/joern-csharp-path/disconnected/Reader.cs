namespace Demo { public static class Reader {
 public static string Read(string value) {
  return System.IO.File.ReadAllText("/srv/files/" + value);
 }
} }
