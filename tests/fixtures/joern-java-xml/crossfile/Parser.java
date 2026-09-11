import javax.xml.parsers.*;
import org.xml.sax.InputSource;
import java.io.StringReader;
class Parser { static Object parse(String data) throws Exception {
    DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
    factory.setFeature("http://xml.org/sax/features/external-general-entities", true);
    DocumentBuilder builder = factory.newDocumentBuilder();
    return builder.parse(new InputSource(new StringReader(data)));
} }
