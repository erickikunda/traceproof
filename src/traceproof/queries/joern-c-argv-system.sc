@main def exec(cpgFile: String, outFile: String) = {
  importCpg(cpgFile)
  val argv = cpg.method.fullNameExact("main").parameter.index(2)
    .filter(p => Set("char**", "char[]*").contains(p.typeFullName)).map(_.id).toSet
  def sources = cpg.call.nameExact("<operator>.indirectIndexAccess").filter { call =>
    Iterator(call.argument(1)).isIdentifier.flatMap(_.refOut).exists(p => argv.contains(p.id)) &&
    Iterator(call.argument(2)).isLiteral.exists(_.code.matches("[1-9][0-9]*"))
  }
  val localSystem = cpg.method.nameExact("system").isExternal(false).nonEmpty
  def sinks = cpg.call.methodFullNameExact("system").filter(_ => !localSystem).argument(1)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "2", "engine_id" -> "joern",
    "rule_id" -> "traceproof/joern-c-argv-system-v1",
    "represented_c_files" -> ujson.Arr.from(cpg.file.name.l.filter(n => n.endsWith(".c") || n.endsWith(".h")).distinct.sorted),
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
