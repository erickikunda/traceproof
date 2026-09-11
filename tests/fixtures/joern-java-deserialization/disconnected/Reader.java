import java.io.*;
import java.util.Base64;
class Reader {
 static Object read(String data) throws Exception {
  return new ObjectInputStream(new ByteArrayInputStream(Base64.getDecoder().decode(data))).readObject();
 }
}
