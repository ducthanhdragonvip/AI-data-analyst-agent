import re


MUTATING_TOKENS = {
    "alter",
    "analyze",
    "call",
    "copy",
    "create",
    "delete",
    "drop",
    "execute",
    "grant",
    "insert",
    "merge",
    "refresh",
    "reindex",
    "replace",
    "revoke",
    "truncate",
    "update",
    "vacuum",
}


def ensure_readonly_select(query: str) -> str:
    normalized = query.strip().rstrip(";")
    if not normalized:
        raise ValueError("SQL query is empty")
    if ";" in normalized:
        raise ValueError("Only one SQL statement is allowed")

    compact = re.sub(r"\s+", " ", normalized).strip()
    first_token = compact.split(" ", 1)[0].lower()
    if first_token not in {"select", "with"}:
        raise ValueError("Only SELECT queries are allowed")

    tokens = {token.lower() for token in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", compact)}
    blocked = MUTATING_TOKENS.intersection(tokens)
    if blocked:
        raise ValueError(f"SQL contains blocked token: {sorted(blocked)[0]}")
    return normalized
