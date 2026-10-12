# study_lens

A PyQt6 drawing app. The window is titled Study Partner. It draws ink on a page with a pencil and an eraser, and it can open a PDF or start a blank note.

Pen color and width, undo and redo, and saving the ink are included. Touch gestures cover the pen, pan, pinch, and swipe.

## Tech

- Python, PyQt6 for the window, canvas, and gestures
- PyMuPDF for opening PDFs
- FastAPI and Uvicorn for a small local backend (`src/backend/main.py`)
- `unittest`-style tests run with pytest

## Layout

- `src/frontend/main_window.py`: the main window. It loads the toolbar modules and gestures listed in `config.json`.
- `src/frontend/modules/`: toolbar modules (open PDF, close PDF, navigation, new note, pen settings, undo/redo, save).
- `src/frontend/gestures/`: pen, pan, pinch, swipe, and clipboard handlers.
- `src/frontend/ink_canvas.py`, `pdf_viewer.py`, `undo_manager.py`: the ink scene, the PDF view, and the undo stack.
- `src/backend/main.py`: a FastAPI app with `/`, `/context` (GET, POST, DELETE), and `/prompts`, which serves `src/backend/prompts.json`.
- `gemini_assisted_llm_studier.md`: the original design spec.

## Setup

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Running

From the repository root (the commands in `commands_to_run.txt`):

```sh
python -m src.frontend.main_window          # the drawing app
uvicorn src.backend.main:app --reload       # the backend, optional
```

## Tests

```sh
pip install pytest
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_undo_redo.py
```

`tests/test_undo_redo.py` checks adding, undoing, and redoing strokes and erases on the ink canvas. CI runs it headless with the Qt `offscreen` platform. The other files in `tests/` (`reproduce_lasso_issue.py`, `verify_*.py`) are manual scripts.

## License

MIT, see `LICENSE`.
