import java.sql.*;
class LookupRepository {
  static Connection connection;
  static void find(String value) throws Exception {
    Statement stmt = connection.createStatement();
    stmt.executeQuery("SELECT id FROM users WHERE name = '" + value + "'");
  }
}
