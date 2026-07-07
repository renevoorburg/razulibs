# Coding Guidelines

RAZU Coding Guideline v0.2 

## Naming

- **Variables and functions**: `snake_case` — e.g. `archive_creator_id`
- **Classes**: `PascalCase` — e.g. `MetaResource`
- **Constants**: `UPPER_SNAKE_CASE` — e.g. `REPOSITORY_ID`, `RUN_INFO_SUFFIX`
- **Private methods**: `_` prefix — e.g. `_load`, `_next_uri`
- **Properties** for derived/computed values, no `get_` prefix — e.g. `uid`, `filename`
- **Booleans**: `is_`/`has_`/`use_` prefix — e.g. `is_modified`, `has_referenced_file`, `use_cache`

## Type hints

- Use `typing` (`Optional`, `List`, `Dict`, `Callable`) or modern union syntax (`str | None`) on public method signatures.
- Not required everywhere, but expected on public APIs.

## Patterns

- **Factory classmethods** `create_new()` / `load_existing()` instead of complex `__init__`.
- **`@dataclass`** for pure data classes.
- **`@staticmethod`** for helper methods without instance state.
- **`@property`** for computed attributes, not for side-effects.
- **Decorators** for cross-cutting concerns (e.g. `@unless_locked`).
- **`is_modified` flag** to track whether an object needs saving (lazy save).

## Libraries

Some preferred libraries:

| Purpose | Library |
|---|---|
| RDF | `rdflib` |
| Linked data serialization | json-ld / turtle (via rdflib) |
| SPARQL | `SPARQLWrapper` |
| S3 / object storage | `boto3` |
| Config | `PyYAML` |
| Secrets / env | `python-dotenv` |
| Paths | `pathlib.Path` (preferred), `os.path` (legacy) |
| Services | `gunicorn` |
| CSV / tabular data | `pandas` |
| Hashing | `hashlib` (MD5) |
| CLI | `argparse` |
| Tests | `pytest` with fixtures |
| Caching | `functools.lru_cache` |

## Style rules

Better using typing and returns than docstrings.
TODO...