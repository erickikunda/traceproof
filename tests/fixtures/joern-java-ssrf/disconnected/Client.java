import java.net.URL;
class Client {
 static java.io.InputStream fetch(String value) throws Exception {
  return new URL(value).openStream();
 }
}
