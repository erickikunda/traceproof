# Java/Spring explicit XML entity discovery (CWE-611)

`java-spring-xml-entities-v1` selects public Spring GetMapping String RequestParam
flow through InputSource/StringReader into DocumentBuilder.parse(InputSource).
The graph must also contain a literal external-general-entities=true feature call
on the factory binding used to create that builder. Direct local variable bindings
connect the feature call, newDocumentBuilder and parse receiver. A feature call on
an unrelated factory is insufficient.

```sh
veriflow --state-dir /path/to/state scan-run RUN_ID --engine joern \
  --language java --joern-home /path/to/joern-cli \
  --joern-profile java-spring-xml-entities-v1
```

Automatic selection includes this profile with the other bounded Java checks, each
with a separate report ID. scan-import accepts the same options. Use get-report
REPO_ID --report-id REPORT_ID --format html for sharing, or json/scan-csv/candidates-csv
for integration. Reports preserve CWE-611 scope and rule identity.

The required literal setting is:

```java
factory.setFeature("http://xml.org/sax/features/external-general-entities", true);
```

These are candidates, not proof of actual external access. Configuration ordering,
variable reassignment, overrides, custom resolvers, secure-processing settings and
external-access restrictions are unverified. A true setting followed by a protective
override can still yield a candidate. Inspect configuration around the retained
source; the rule does not reconstruct final parser state or certify hardening.
Oracle documents the interaction of these controls in its
[JAXP security guide](https://docs.oracle.com/en/java/javase/25/security/java-api-xml-processing-jaxp-security-guide.html).

Disabled-only or missing settings are excluded from this initial profile. That is
unsupported configuration scope, not a safe verdict: default parsers may still be
vulnerable. Constant XML and unrelated parse methods are negative fixtures. A length
guard does not suppress a candidate. All new candidates remain advisory-unsupported.

Other HTTP bindings, InputStream/String parse overloads, SAX/StAX/transformers,
configuration helpers, factory aliases, subclass overrides and nonliteral feature
values remain gaps. The profile requires the direct local binding shape, while
request data can reach the parser through a cross-file helper. Unknown external
method semantics may overapproximate data flow; no runtime package identity claim.

No XML entities, source code or network requests are executed during scanning.
No model calls or migration. Native validation installs the wheel in restricted
Linux scratch; published images and bank OCP acceptance remain unchanged.
