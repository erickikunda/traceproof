import java.sql.*;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class LookupController {
    private final Connection connection;
    public LookupController(Connection connection) { this.connection = connection; }

    @GetMapping("/lookup")
    public ResultSet lookup(@RequestParam String name) throws SQLException {
        return connection.createStatement().executeQuery("SELECT * FROM users WHERE name='" + name + "'");
    }
}
