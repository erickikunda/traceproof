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
  val responses = handlers.flatMap(_.parameter.l.filter(_.index == 2)).map(_.id).toSet
  // The frontend lowers a chained receiver into an assignment to a temporary.
  val htmlReceivers = cpg.call.nameExact("<operator>.assignment").flatMap { assignment =>
    Iterator(assignment.argument(2)).isCall.nameExact("type").filter { typed =>
      Set("\"html\"", "'html'", "\"text/html\"", "'text/html'").contains(typed.argument(1).code) &&
      Iterator(typed.argument(0)).isIdentifier.flatMap(_.refOut).exists(p => responses.contains(p.id))
    }.flatMap { typed =>
      Iterator(assignment.argument(1)).isIdentifier.flatMap(_.refOut).map(p => (p.id, typed.code))
    }
  }.l
  def sinks = cpg.call.nameExact("send").filter { send =>
    Iterator(send.argument(0)).isIdentifier.flatMap(_.refOut).exists { receiver =>
      htmlReceivers.exists { case (id, code) =>
        id == receiver.id && send.code.startsWith(code + ".send(")
      }
    }
  }.argument(1)
  val flows = sinks.reachableByFlows(sources).l
  val result = ujson.Obj(
    "schema_version" -> "2", "engine_id" -> "joern",
    "rule_id" -> "veriflow/joern-javascript-express-html-send-v1",
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
