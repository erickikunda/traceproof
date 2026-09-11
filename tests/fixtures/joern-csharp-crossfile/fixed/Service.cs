using System.Data.Common;
public class SearchService {
  public static DbDataReader Find(string term, DbConnection connection) {
    return SearchRepository.Find(term, connection);
  }
}
