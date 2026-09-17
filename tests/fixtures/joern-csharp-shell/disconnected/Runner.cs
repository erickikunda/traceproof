namespace Demo { public static class Runner {
 public static object Run(string value) {
  return System.Diagnostics.Process.Start("/bin/sh", "-c \"" + value + "\"");
 }
} }
