@main def exec(cpgFile: String, outFile: String) = {
  importCpg(cpgFile)
  def sources = cpg.method.filter(m =>
    m.annotation.fullName.l.contains("org.springframework.web.bind.annotation.GetMapping") &&
    m.modifier.modifierType.l.contains("PUBLIC")
  ).parameter.filter(p =>
    p.typeFullName == "java.lang.String" &&
    p.annotation.fullName.l.contains("org.springframework.web.bind.annotation.RequestParam")
  )
  def sinks = cpg.call.methodFullNameExact(
    "java.sql.Statement.executeQuery:java.sql.ResultSet(java.lang.String)"
  ).argument(1)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "2",
    "engine_id" -> "joern",
    "rule_id" -> "traceproof/joern-spring-get-jdbc-sql-v1",
    "represented_java_files" -> ujson.Arr.from(cpg.file.name.l.filter(_.endsWith(".java")).distinct.sorted),
    "source_count" -> sources.size,
    "sink_count" -> sinks.size,
    "flow_count" -> flows.size,
    "paths" -> ujson.Arr.from(flows.map(p => ujson.Arr.from(p.elements.map(n => ujson.Obj(
      "code" -> n.code,
      "file" -> n.file.name.headOption.getOrElse(""),
      "line" -> n.lineNumber.getOrElse(-1)
    ))))),
    "qualification" -> "bounded_spring_jdbc_discovery"
  )
  java.nio.file.Files.writeString(java.nio.file.Path.of(outFile), ujson.write(result, indent = 2))
}
