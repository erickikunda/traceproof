@main def exec(cpgFile: String, outFile: String) = {
  importCpg(cpgFile)
  def sources = cpg.method.filter(m =>
    m.annotation.fullName.l.contains("org.springframework.web.bind.annotation.GetMapping") &&
    m.modifier.modifierType.l.contains("PUBLIC")
  ).parameter.filter(p =>
    p.typeFullName == "java.lang.String" &&
    p.annotation.fullName.l.contains("org.springframework.web.bind.annotation.RequestParam")
  )
  val configuredFactories = cpg.call.methodFullNameExact(
    "javax.xml.parsers.DocumentBuilderFactory.setFeature:void(java.lang.String,boolean)"
  ).filter(c => c.argument(1).code == "\"http://xml.org/sax/features/external-general-entities\"" &&
    c.argument(2).code == "true").argument(0).isIdentifier.flatMap(_.refOut).map(_.id).toSet
  val builders = cpg.call.nameExact("<operator>.assignment").filter { assignment =>
    Iterator(assignment.argument(2)).isCall.methodFullNameExact(
      "javax.xml.parsers.DocumentBuilderFactory.newDocumentBuilder:javax.xml.parsers.DocumentBuilder()"
    ).argument(0).isIdentifier.flatMap(_.refOut).exists(p => configuredFactories.contains(p.id))
  }.argument(1).isIdentifier.flatMap(_.refOut).map(_.id).toSet
  def sinks = cpg.call.methodFullNameExact(
    "javax.xml.parsers.DocumentBuilder.parse:org.w3c.dom.Document(org.xml.sax.InputSource)"
  ).filter(c => Iterator(c.argument(0)).isIdentifier.flatMap(_.refOut).exists(p => builders.contains(p.id))).argument(1)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "2",
    "engine_id" -> "joern",
    "rule_id" -> "traceproof/joern-spring-get-xml-entities-v1",
    "represented_java_files" -> ujson.Arr.from(cpg.file.name.l.filter(_.endsWith(".java")).distinct.sorted),
    "source_count" -> sources.size,
    "sink_count" -> sinks.size,
    "flow_count" -> flows.size,
    "paths" -> ujson.Arr.from(flows.map(p => ujson.Arr.from(p.elements.map(n => ujson.Obj(
      "code" -> n.code,
      "file" -> n.file.name.headOption.getOrElse(""),
      "line" -> n.lineNumber.getOrElse(-1)
    ))))),
    "qualification" -> "bounded_spring_explicit_xml_entities_discovery"
  )
  java.nio.file.Files.writeString(java.nio.file.Path.of(outFile), ujson.write(result, indent = 2))
}
