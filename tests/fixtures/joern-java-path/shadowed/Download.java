import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import java.nio.file.Files;
import java.nio.file.Path;
class Download {
  @GetMapping("/download")
  public byte[] read(@RequestParam String name) throws Exception {
    return Other.readAllBytes(Path.of(name));
  }
}
