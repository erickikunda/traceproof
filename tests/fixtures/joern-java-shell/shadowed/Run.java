import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
class Run {
 @GetMapping("/run")
 public Process run(@RequestParam String data) throws Exception {
    return new Other().exec(new String[]{"/bin/sh", "-c", data});
 }
}
class Other { Process exec(String[] args) { return null; } }
