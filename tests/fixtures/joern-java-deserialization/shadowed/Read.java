import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import java.io.*;
import java.util.Base64;
class Read {
  @GetMapping("/read")
  public Object read(@RequestParam String data) throws Exception {
    return new Other(data).readObject();
  }
}
class Other { Other(String value) {} Object readObject() { return null; } }
