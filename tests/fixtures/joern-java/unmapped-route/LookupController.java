import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.GetMapping;
class LookupController {
  public void lookup(@RequestParam String name) throws Exception {
    LookupService.find(name);
  }
}
