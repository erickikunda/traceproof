import java.sql.*;
class LookupRepository {
  static Connection connection;
  static void find(String value) throws Exception {
    FakeStatement stmt = new FakeStatement();
    stmt.executeQuery("SELECT id FROM users WHERE name = '" + value + "'");
  }
}

class FakeStatement { void executeQuery(String sql) {} }
