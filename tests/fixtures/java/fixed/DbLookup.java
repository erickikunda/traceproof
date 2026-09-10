import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

public class DbLookup {
    public ResultSet lookup(Connection connection, String name) throws SQLException {
        PreparedStatement query = connection.prepareStatement(
            "SELECT id FROM accounts WHERE name = ?");
        query.setString(1, name);
        return query.executeQuery();
    }
}
