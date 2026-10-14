import { assertNever, parsePageNumber, type ModuleId, type PenSettings, type SessionView, type StudySession, type Tool } from '@study-lens/core';
import { useEffect, useState, type ReactElement } from 'react';
import { PenSettingsDialog } from './pen-settings';

interface ToolbarProps {
  modules: ModuleId[];
  session: StudySession;
  view: SessionView;
  recentPens: PenSettings[];
  onRecentPens: (pens: PenSettings[]) => void;
  onOpen: () => void;
  onSave: () => void;
  onClose: () => void;
  onNewNote: () => void;
}

export function Toolbar(props: ToolbarProps): ReactElement {
  return (
    <header className="toolbar">
      <p className="wordmark">Study Partner</p>
      {props.modules.map((id) => (
        <ModuleControl key={id} id={id} {...props} />
      ))}
    </header>
  );
}

function ModuleControl(props: ToolbarProps & { id: ModuleId }): ReactElement {
  const disabled = !props.view.hasDocument;
  switch (props.id) {
    case 'open-pdf':
      return (
        <button type="button" onClick={props.onOpen}>
          Open PDF
        </button>
      );
    case 'navigation':
      return <Navigation session={props.session} view={props.view} />;
    case 'undo-redo':
      return <History session={props.session} view={props.view} />;
    case 'new-note':
      return (
        <button type="button" onClick={props.onNewNote}>
          New Note
        </button>
      );
    case 'save':
      return (
        <button type="button" onClick={props.onSave} disabled={disabled}>
          Save
        </button>
      );
    case 'pen-settings':
      return (
        <PenControls
          session={props.session}
          view={props.view}
          recentPens={props.recentPens}
          onRecentPens={props.onRecentPens}
          disabled={disabled}
        />
      );
    case 'close-pdf':
      return (
        <button type="button" onClick={props.onClose} disabled={disabled}>
          Close
        </button>
      );
    default:
      return assertNever(props.id);
  }
}

function Navigation(props: { session: StudySession; view: SessionView }): ReactElement {
  const { view, session } = props;
  const [draft, setDraft] = useState(view.hasDocument ? String(view.pageIndex + 1) : '0');
  useEffect(() => {
    setDraft(view.hasDocument ? String(view.pageIndex + 1) : '0');
  }, [view.hasDocument, view.pageIndex, view.pageCount]);

  return (
    <div className="cluster" role="group" aria-label="Page navigation">
      <button type="button" aria-label="Back 5 pages" disabled={!view.hasDocument} onClick={() => void session.changePage(-5)}>
        {'<<'}
      </button>
      <button type="button" aria-label="Previous page" disabled={!view.hasDocument} onClick={() => void session.changePage(-1)}>
        {'<'}
      </button>
      <input
        aria-label="Page number"
        data-testid="page-number"
        value={draft}
        disabled={!view.hasDocument}
        inputMode="decimal"
        onChange={(event) => setDraft(event.target.value)}
        onKeyDown={(event) => {
          if (event.key !== 'Enter') return;
          const pageNumber = parsePageNumber(draft);
          if (pageNumber === null) {
            setDraft(String(view.pageIndex + 1));
            return;
          }
          void session.goTo(pageNumber - 1);
        }}
      />
      <span>/ {view.pageCount}</span>
      <button type="button" aria-label="Next page" disabled={!view.hasDocument} onClick={() => void session.changePage(1)}>
        {'>'}
      </button>
      <button type="button" aria-label="Forward 5 pages" disabled={!view.hasDocument} onClick={() => void session.changePage(5)}>
        {'>>'}
      </button>
    </div>
  );
}

function History(props: { session: StudySession; view: SessionView }): ReactElement {
  const { view, session } = props;
  return (
    <div className="cluster" role="group" aria-label="Undo and redo">
      <button type="button" aria-label="Undo 5" disabled={view.historyCurrent === 0} onClick={() => session.undo(5)}>
        {'<<'}
      </button>
      <button type="button" aria-label="Undo" disabled={view.historyCurrent === 0} onClick={() => session.undo(1)}>
        {'<'}
      </button>
      <span data-testid="history">
        {view.historyCurrent} / {view.historyTotal}
      </span>
      <button
        type="button"
        aria-label="Redo"
        disabled={view.historyCurrent >= view.historyTotal}
        onClick={() => session.redo(1)}
      >
        {'>'}
      </button>
      <button
        type="button"
        aria-label="Redo 5"
        disabled={view.historyCurrent >= view.historyTotal}
        onClick={() => session.redo(5)}
      >
        {'>>'}
      </button>
    </div>
  );
}

function PenControls(props: {
  session: StudySession;
  view: SessionView;
  recentPens: PenSettings[];
  onRecentPens: (pens: PenSettings[]) => void;
  disabled: boolean;
}): ReactElement {
  const [open, setOpen] = useState(false);
  const tools: Array<{ id: Tool; label: string }> = [
    { id: 'pencil', label: 'Pencil' },
    { id: 'eraser', label: 'Eraser' },
    { id: 'lasso', label: 'Lasso' },
  ];
  return (
    <div className="cluster pen-controls">
      {tools.map((tool) => (
        <button
          key={tool.id}
          type="button"
          aria-pressed={props.view.tool === tool.id}
          disabled={props.disabled}
          onClick={() => props.session.setTool(tool.id)}
        >
          {tool.label}
        </button>
      ))}
      <button type="button" disabled={props.disabled} onClick={() => setOpen((value) => !value)}>
        Pen Settings
      </button>
      {open ? (
        <PenSettingsDialog
          pen={props.view.pen}
          recent={props.recentPens}
          onChange={(pen) => props.session.setPen(pen)}
          onRecent={props.onRecentPens}
          onClose={() => setOpen(false)}
        />
      ) : null}
    </div>
  );
}
