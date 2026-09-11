import java.sql.*;
class LookupRepository {
  static Connection connection;
  static void find(String value) throws Exception {
    PreparedStatement stmt = connection.prepareStatement("SELECT id FROM users WHERE name = ?");
    stmt.setString(1, value);
    stmt.executeQuery();
  }
}
