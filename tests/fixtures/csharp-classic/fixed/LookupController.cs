using System.Data.SqlClient;
using System.Web;
public class LookupController {
    public SqlDataReader Lookup(HttpRequest request, SqlConnection connection) {
        string name = request.QueryString["name"];
        var command = new SqlCommand("SELECT * FROM users WHERE name=@name", connection);
        command.Parameters.AddWithValue("@name", name);
        return command.ExecuteReader();
    }
}
