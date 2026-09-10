"""Source-only Spring annotation/SQL path acceptance; not a Spring build qualification.

Usage: uv run python scripts/validate_spring.py QUERY_PATH NEW_OUTPUT_DIRECTORY
Expected query: codeql/java-queries Security/CWE/CWE-089/SqlTainted.ql.
"""

from validate_java import main

if __name__ == "__main__":
    main("spring")
