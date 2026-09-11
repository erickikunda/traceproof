import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
class Run {
 @GetMapping("/run")
 public Process run(@RequestParam String data) throws Exception {
    String unused = data; return null;
 }
}
