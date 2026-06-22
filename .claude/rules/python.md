---
paths: ["**/*.py"]
---

- Type hints on all function signatures, including return types
- Use `pathlib.Path` for filesystem operations, not `os.path`
- SQLite: use parameterized queries, never f-string SQL
- FastAPI: use Pydantic models for request bodies, not raw dicts
- Keep functions under ~30 lines; extract helpers when they grow
