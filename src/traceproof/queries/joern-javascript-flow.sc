@main def exec(cpgFile: String, outFile: String) = {
  importCpg(cpgFile)
  def sources = cpg.method.nameExact("lookup").parameter.nameExact("input")
  def sinks = cpg.call.nameExact("eval").argument(1)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "2", "engine_id" -> "joern",
    "rule_id" -> "traceproof/joern-javascript-lookup-eval-v1",
    "represented_javascript_files" -> ujson.Arr.from(cpg.file.name.l.filter(_.endsWith(".js")).distinct.sorted),
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
