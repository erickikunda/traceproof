import java.sql.*;
import example.lookalike.GetMapping;
import example.lookalike.RequestParam;
import example.lookalike.RestController;

@RestController
public class LookupController {
    private final Connection connection;
    public LookupController(Connection connection) { this.connection = connection; }

    @GetMapping("/lookup")
    public ResultSet lookup(@RequestParam String name) throws SQLException {
        return connection.createStatement().executeQuery("SELECT * FROM users WHERE name='" + name + "'");
    }
}
