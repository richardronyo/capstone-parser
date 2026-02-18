from tree_sitter import Parser, Language
from pygments.lexers import guess_lexer_for_filename

from tree_sitter_python import language as python_capsule
from tree_sitter_javascript import language as js_capsule
from tree_sitter_typescript import language_typescript
from tree_sitter_java import language as java_capsule
from tree_sitter_go import language as go_capsule
from tree_sitter_rust import language as rust_capsule
from tree_sitter_c import language as c_capsule
from tree_sitter_cpp import language as cpp_capsule
from tree_sitter_c_sharp import language as csharp_capsule


# ---------------------------------------------------------------------------
# Language registry — single canonical key per language
# ---------------------------------------------------------------------------

LANGUAGE_MAP = {
    "python":     Language(python_capsule()),
    "javascript": Language(js_capsule()),
    "typescript": Language(language_typescript()),
    "java":       Language(java_capsule()),
    "go":         Language(go_capsule()),
    "rust":       Language(rust_capsule()),
    "c":          Language(c_capsule()),
    "cpp":        Language(cpp_capsule()),
    "csharp":     Language(csharp_capsule()),
}

# Pygments returns many variant names — normalise them all to canonical keys
LANGUAGE_ALIASES = {
    "c#":        "csharp",
    "c sharp":   "csharp",
    "csharp":    "csharp",
    "c# (mono)": "csharp",
    "python":    "python",
    "python 3":  "python",
    "javascript":"javascript",
    "typescript":"typescript",
    "java":      "java",
    "go":        "go",
    "rust":      "rust",
    "c":         "c",
    "c++":       "cpp",
    "c/c++":     "cpp",
}

# Minimal-API style route methods to detect as pseudo-methods
ROUTE_METHODS = {"MapGet", "MapPost", "MapPut", "MapPatch", "MapDelete"}


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def detect_language(filename: str, code: str) -> str:
    """Detect language from filename + content via Pygments, then normalise."""
    try:
        lexer = guess_lexer_for_filename(filename, code)
        raw = lexer.name.lower()
        return LANGUAGE_ALIASES.get(raw, raw)
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------

def get_node_name(node, code: str) -> str:
    """
    Return the identifier/name child of a node, or 'unknown'.
    Checks direct children only; works for class/method/function declarations.
    """
    for child in node.children:
        if child.type in ("identifier", "name", "type_identifier"):
            return code[child.start_byte:child.end_byte]
    return "unknown"


def get_invocation_name(node, code: str) -> str:
    """
    For an invocation_expression node, extract the called method name.
    Handles both  `api.MapGet(...)` and plain `MapGet(...)`.
    """
    if not node.children:
        return "unknown"
    callee = node.children[0]
    text = code[callee.start_byte:callee.end_byte]
    # Return just the final segment (e.g. "api.MapGet" → "MapGet")
    return text.split(".")[-1] if "." in text else text


# ---------------------------------------------------------------------------
# Structure extraction
# ---------------------------------------------------------------------------

def extract_structure(language_name: str, code: str, filename: str = "") -> dict:
    if language_name not in LANGUAGE_MAP:
        return {
            "language": language_name,
            "error": f"Language '{language_name}' is not supported.",
            "components": [],
        }

    parser = Parser(LANGUAGE_MAP[language_name])
    tree = parser.parse(code.encode("utf-8"))
    root = tree.root_node

    components = []

    def make_component(type_, name, node, class_name=None):
        snippet = code[node.start_byte:node.end_byte]
        # Normalize indentation — strip common leading whitespace
        lines = snippet.splitlines()
        if lines:
            indent = len(lines[0]) - len(lines[0].lstrip())
            lines = [l[indent:] for l in lines]
        snippet = "\n".join(lines).strip()

        entry = {
            "type":  type_,
            "name":  name,
            "lines": f"{node.start_point[0] + 1}-{node.end_point[0] + 1}",
            "code":  snippet,
        }
        if class_name:
            entry["class"] = class_name
        components.append(entry)

    def walk(node, current_class=None):
        if node.type in ("class_definition", "class_declaration"):
            class_name = get_node_name(node, code)
            make_component("class", class_name, node)  # no code field for classes
            components[-1].pop("code")                 # drop it
            for child in node.children:
                walk(child, class_name)
            return

        if node.type in (
            "function_definition", "function_declaration",
            "method_definition", "method_declaration",
            "constructor_declaration",
        ):
            make_component("method" if current_class else "function",
                           get_node_name(node, code), node, current_class)

        if node.type == "invocation_expression":
            method_name = get_invocation_name(node, code)
            if method_name in ROUTE_METHODS:
                # Use the route path as the name if we can find it
                args = [c for c in node.children if c.type == "argument_list"]
                route_path = "?"
                if args and args[0].children:
                    first_arg = args[0].children[0]
                    route_path = code[first_arg.start_byte:first_arg.end_byte].strip('"')
                make_component("route", f"{method_name} {route_path}",
                               node, current_class)
                return

        for child in node.children:
            walk(child, current_class)

    walk(root)

    method_count  = sum(1 for c in components if c["type"] == "method")
    function_count = sum(1 for c in components if c["type"] == "function")
    class_count   = sum(1 for c in components if c["type"] == "class")
    route_count   = sum(1 for c in components if c["type"] == "route")

    return {
        "language":   language_name,
        "file":       filename,
        "summary":    {
            "classes":   class_count,
            "methods":   method_count,
            "functions": function_count,
            "routes":    route_count,
        },
        "components": components,
    }

