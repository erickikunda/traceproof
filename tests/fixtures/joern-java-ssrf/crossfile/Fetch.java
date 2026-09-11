import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import java.net.URL;
import java.io.InputStream;
class Fetch {
  @GetMapping("/fetch")
  public InputStream fetch(@RequestParam String url) throws Exception {
    return Client.fetch(url);
  }
}
