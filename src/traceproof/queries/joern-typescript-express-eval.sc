@main def exec(cpgFile: String, outFile: String) = {
  importCpg(cpgFile)
  val handlers = cpg.call.methodFullNameExact(
    "express:express:<returnValue>:get", "express:express:<returnValue>:post"
  ).argument(2).isMethodRef.map(_.referencedMethod).l
  val parameters = handlers.flatMap(_.parameter.l.filter(_.index == 1)).map(_.id).toSet
  // Select req.query.field, req.body.field or req.params.field, not the whole request.
  def sources = cpg.call.nameExact("<operator>.fieldAccess").filter { outer =>
    Iterator(outer.argument(1)).isCall.nameExact("<operator>.fieldAccess").exists { inner =>
      Set("query", "body", "params").contains(inner.argument(2).code) &&
      Iterator(inner.argument(1)).isIdentifier.flatMap(_.refOut).exists(p => parameters.contains(p.id))
    }
  }
  def sinks = cpg.call.methodFullNameExact("eval").argument(1)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "2", "engine_id" -> "joern",
    "rule_id" -> "traceproof/joern-typescript-express-eval-v1",
    "represented_typescript_files" -> ujson.Arr.from(cpg.file.name.l.filter(_.endsWith(".ts")).distinct.sorted),
    "source_count" -> sources.size, "sink_count" -> sinks.size,
    "method_names" -> ujson.Arr.from(cpg.method.name.l.distinct.sorted),
    "call_names" -> ujson.Arr.from(cpg.call.name.l.distinct.sorted),
    "flow_count" -> flows.size,
    "paths" -> ujson.Arr.from(flows.map(p => ujson.Arr.from(p.elements.map(n => ujson.Obj(
      "code" -> n.code, "file" -> n.file.name.headOption.getOrElse(""),
      "line" -> n.lineNumber.getOrElse(-1)
    ))))),
    "qualification" -> "fixture_feasibility_only"
  )
  java.nio.file.Files.writeString(java.nio.file.Path.of(outFile), ujson.write(result, indent = 2))
}
