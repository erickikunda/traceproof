import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.GetMapping;
class LookupController {
  @GetMapping("/lookup")
  public void search(@RequestParam String term) throws Exception {
    LookupService.find(term);
  }
}
