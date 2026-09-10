using System.Data.Common;
using System.Net.Sockets;
using System.IO;
public class NetworkLookup {
    public DbDataReader Lookup(TcpClient client, DbConnection connection) {
        string name = new StreamReader(client.GetStream()).ReadLine();
        var command = connection.CreateCommand();
        command.CommandText = "SELECT * FROM users WHERE name='" + name + "'";
        return command.ExecuteReader();
    }
}
