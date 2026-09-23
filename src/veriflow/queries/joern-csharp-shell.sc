@main def exec(cpgFile: String, outFile: String) = {
  importCpg(cpgFile)
  def sources = cpg.method.parameter.filter(_.index > 0)
  val localLookalike = cpg.typeDecl.filter(t =>
    !t.isExternal && Set("System", "Diagnostics", "Process").contains(t.name)
  ).nonEmpty
  def sinks = cpg.call.nameExact("Start").filter(c =>
    !localLookalike && c.argument(0).code == "System.Diagnostics.Process" &&
    c.argument.size == 3 &&
    Set("\"sh\"", "\"/bin/sh\"", "\"bash\"", "\"/bin/bash\"").contains(c.argument(1).code) &&
    c.argument(2).code.startsWith("\"-c ")
  ).argument(2)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "2", "engine_id" -> "joern",
    "rule_id" -> "veriflow/joern-csharp-query-shell-start-v1",
    "represented_csharp_files" -> ujson.Arr.from(cpg.file.name.l.filter(_.endsWith(".cs")).distinct.sorted),
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
