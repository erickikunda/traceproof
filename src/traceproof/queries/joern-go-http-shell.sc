@main def exec(cpgFile: String, outFile: String) = {
  importCpg(cpgFile)
  def sources = cpg.call.methodFullNameExact(
    "net/http.Request.FormValue", "net/http.Request.PostFormValue"
  )
  // A normal process argument is not automatically shell command text.
  def sinks = cpg.call.methodFullNameExact("os/exec.Command").filter { call =>
    call.argument.l.size == 3 &&
    Iterator(call.argument(1)).isLiteral.codeExact("\"sh\"", "\"bash\"", "\"/bin/sh\"", "\"/bin/bash\"").nonEmpty &&
    Iterator(call.argument(2)).isLiteral.codeExact("\"-c\"").nonEmpty
  }.argument(3)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "2", "engine_id" -> "joern",
    "rule_id" -> "traceproof/joern-go-http-shell-v1",
    "represented_go_files" -> ujson.Arr.from(cpg.file.name.l.filter(_.endsWith(".go")).distinct.sorted),
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
