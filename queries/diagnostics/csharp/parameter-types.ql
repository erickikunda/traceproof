import csharp
from Parameter p, string status
where p.fromSource() and p.getName() in ["request", "connection"] and
  ((p.getType() instanceof UnknownType and status = "unknown") or
   (not p.getType() instanceof UnknownType and status = "resolved"))
select p.getName(), p.getType().toString(), status
