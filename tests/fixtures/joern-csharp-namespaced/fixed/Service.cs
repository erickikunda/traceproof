using System.Data.Common;
namespace TraceProofProbe {
public class SearchService {
  public static DbDataReader Find(string term, DbConnection connection) {
    return SearchRepository.Find(term, connection);
  }
}
}
