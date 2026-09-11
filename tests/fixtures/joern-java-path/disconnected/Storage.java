import java.nio.file.*;
class Storage {
 static byte[] read(String value) throws Exception {
  return Files.readAllBytes(Path.of("/srv/files/" + value));
 }
}
