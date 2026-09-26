@main def exec(cpgFile: String, outFile: String) = {
  importCpg(cpgFile)
  import io.shiftleft.codepropertygraph.generated.nodes.{Call, Expression}
  val wrappers = Set("<operator>.addressOf", "<operator>.indirection")
  def receiver(n: Call): Option[Call] = {
    def strip(e: Expression, remaining: Int): Option[Call] = e match {
      case c: Call if wrappers.contains(c.name) && remaining > 0 =>
        c.argument.l.find(_.argumentIndex == 1).flatMap(strip(_, remaining - 1))
      case c: Call if !wrappers.contains(c.name) => Some(c)
      case _ => None
    }
    n.argument.l.find(_.argumentIndex == 0).flatMap(strip(_, 4))
  }
  def sources = cpg.call.methodFullNameExact("std::env::var<K>")
    .filter(n => n.argument.l.size == 1 && n.argument.isLiteral.nonEmpty)
  def sinks = cpg.call.methodFullNameExact("std::process::Command::arg<S>").filter { call =>
    receiver(call).exists { flag =>
      flag.methodFullName == "std::process::Command::arg<S>" &&
      flag.argument.isLiteral.argumentIndex(1).codeExact("\"-c\"").nonEmpty &&
      receiver(flag).exists { constructor =>
        constructor.methodFullName == "std::process::Command::new<S>" &&
        constructor.argument.isLiteral.argumentIndex(1)
          .codeExact("\"sh\"", "\"bash\"", "\"/bin/sh\"", "\"/bin/bash\"").nonEmpty
      }
    }
  }.argument(1)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "2", "engine_id" -> "joern",
    "rule_id" -> "veriflow/joern-rust-env-shell-v1",
    "represented_rust_files" -> ujson.Arr.from(cpg.file.name.l.filter(_.endsWith(".rs")).distinct.sorted),
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
