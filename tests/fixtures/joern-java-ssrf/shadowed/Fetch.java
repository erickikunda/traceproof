import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import java.net.URL;
import java.io.InputStream;
class Fetch {
  @GetMapping("/fetch")
  public InputStream fetch(@RequestParam String url) throws Exception {
    return new Other(url).openStream();
  }
}
class Other { Other(String value) {} java.io.InputStream openStream() { return null; } }
