import javax.xml.parsers.*;
import org.xml.sax.InputSource;
import java.io.StringReader;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
class Read {
 @GetMapping("/xml")
 public Object read(@RequestParam String data) throws Exception {
    return new Other().parse(new InputSource(new StringReader(data)));
 }
}
class Other { Object parse(InputSource value) { return null; } }
