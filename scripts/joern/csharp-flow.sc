@main def exec(cpgFile: String, outFile: String) = {
  importCpg(cpgFile)
  def sources = cpg.method.nameExact("Lookup").parameter.nameExact("name")
  def sinks = cpg.call.nameExact("<operator>.assignment").filter(c =>
    c.argument(1).code.endsWith(".CommandText")
  ).argument(2)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "1", "engine_id" -> "joern",
    "rule_id" -> "traceproof/joern-csharp-fixture-flow",
    "source_count" -> sources.size, "sink_count" -> sinks.size,
    "parameter_annotations" -> ujson.Arr.from(sources.annotation.fullName.l),
    "flow_count" -> flows.size,
    "paths" -> ujson.Arr.from(flows.map(p => ujson.Arr.from(p.elements.map(n => ujson.Obj(
      "code" -> n.code, "file" -> n.file.name.headOption.getOrElse(""),
      "line" -> n.lineNumber.getOrElse(-1)
    ))))),
    "qualification" -> "fixture_feasibility_only"
  )
  java.nio.file.Files.writeString(java.nio.file.Path.of(outFile), ujson.write(result, indent = 2))
}
