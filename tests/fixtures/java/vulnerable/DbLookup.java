import java.sql.Connection;
import java.sql.ResultSet;
import java.sql.SQLException;

public class DbLookup {
    public ResultSet lookup(Connection connection, String name) throws SQLException {
        return connection.createStatement().executeQuery(
            "SELECT id FROM accounts WHERE name = '" + name + "'");
    }
}
