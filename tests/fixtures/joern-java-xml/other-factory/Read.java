import javax.xml.parsers.*;
import org.xml.sax.InputSource;
import java.io.StringReader;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
class Read {
 @GetMapping("/xml")
 public Object read(@RequestParam String data) throws Exception {
    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
    factory.setFeature("http://xml.org/sax/features/external-general-entities", true);
    DocumentBuilderFactory other = DocumentBuilderFactory.newInstance();
    DocumentBuilder builder = other.newDocumentBuilder();
    return builder.parse(new InputSource(new StringReader(data)));
 }
}
