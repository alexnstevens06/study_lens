# Legacy Python app

This directory is the previous Study Partner desktop app (PyQt6, PyMuPDF, and a small FastAPI process). It is frozen and is not the supported product.

The supported app is the TypeScript web and desktop build in the repository root. See the root `README.md`.

The old window, toolbar modules, gestures, and API behavior were the source of the rewrite:

- `src/frontend/main_window.py` loads toolbar modules and the PDF view. The window title is Study Partner.
- `src/frontend/modules/` is the toolbar: open PDF, close PDF, page navigation, new note, pen settings, undo/redo, and save.
- `src/frontend/gestures/` handles the pen, pan, pinch, swipe, and clipboard paste.
- `src/frontend/ink_canvas.py`, `pdf_viewer.py`, and `undo_manager.py` are the ink scene, page cache, and command stack.
- `src/backend/main.py` serves `GET /`, `GET`/`POST`/`DELETE /context`, and `GET /prompts`.
- `config.json` is the old module and gesture enablement file (Python paths). The root `config.json` is the file the TypeScript app reads.
- `gemini_assisted_llm_studier.md` is the original design spec.

Committed `__pycache__` directories were removed. They are bytecode, not source.

## Running the legacy app

From this directory's parent (the repository root), paths inside the legacy tree still use `src.*` imports, so run Python with `legacy` on the path:

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r legacy/requirements.txt
cd legacy
python -m src.frontend.main_window
uvicorn src.backend.main:app --reload
```

PyMuPDF is AGPL. That is one reason the supported build does not use it. Do not add this tree back to the shipping product.
