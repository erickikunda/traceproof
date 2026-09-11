@main def exec(cpgFile: String, outFile: String, endpointFile: String) = {
  importCpg(cpgFile)
  val endpoints = ujson.read(java.nio.file.Files.readString(java.nio.file.Path.of(endpointFile)))
  def selected(kind: String) = endpoints.arr.toList.flatMap { file =>
    file(kind).arr.toList.flatMap { ep =>
      val matches = cpg.call.nameExact(ep("name").str).filter(n =>
        n.lineNumber.contains(ep("line").num.toInt) &&
        n.file.name.l.exists(p => p == file("file").str || p == file("absolute_file").str)
      ).l
      if (matches.size == 1) matches else Nil
    }
  }.distinct
  def sources = selected("sources").iterator
  def sinks = selected("sinks").iterator.argument(1)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "2", "engine_id" -> "joern",
    "rule_id" -> "traceproof/joern-python-flask-system-v1",
    "represented_python_files" -> ujson.Arr.from(cpg.file.name.l.filter(_.endsWith(".py")).distinct.sorted),
    "source_count" -> sources.size, "sink_count" -> sinks.size,
    "method_names" -> ujson.Arr.from(cpg.method.name.l.distinct.sorted),
    "call_names" -> ujson.Arr.from(cpg.call.name.l.distinct.sorted),
    "flow_count" -> flows.size,
    "paths" -> ujson.Arr.from(flows.map(p => ujson.Arr.from(p.elements.map(n => ujson.Obj(
      "code" -> n.code, "file" -> n.file.name.headOption.getOrElse(""),
      "line" -> n.lineNumber.getOrElse(-1)
    ))))),
    "qualification" -> "bounded_flask_syntax_discovery"
  )
  java.nio.file.Files.writeString(java.nio.file.Path.of(outFile), ujson.write(result, indent = 2))
}
