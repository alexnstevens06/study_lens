import {
  clonePen,
  enabledGestures,
  enabledModules,
  StudySession,
  type FileAdapter,
  type GestureId,
  type ModuleId,
  type OpenedPdf,
  type PenSettings,
} from '@study-lens/core';
import { useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { createFileAdapter } from './files/create-file-adapter';
import { InkView } from './ink-view';
import { loadAppConfig } from './load-config';
import { Toolbar } from './toolbar';

export function App() {
  const sessionRef = useRef<StudySession | null>(null);
  if (sessionRef.current === null) sessionRef.current = new StudySession();
  const session = sessionRef.current;
  const view = useSyncExternalStore(session.subscribeView, session.getView, session.getView);
  const inputRef = useRef<HTMLInputElement>(null);
  const adapterRef = useRef<FileAdapter | null>(null);
  const pathRef = useRef<string | undefined>(undefined);
  const [modules, setModules] = useState<ModuleId[]>([]);
  const [gestures, setGestures] = useState<Set<GestureId>>(() => new Set());
  const [recentPens, setRecentPens] = useState<PenSettings[]>(() => [clonePen(view.pen)]);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    void loadAppConfig()
      .then((config) => {
        setModules(enabledModules(config).map((module) => module.id));
        setGestures(enabledGestures(config));
      })
      .catch((error: unknown) => {
        setStatus(error instanceof Error ? error.message : 'Could not load config.json');
      });
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent): void => {
      const target = event.target;
      if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) return;
      if (!(event.ctrlKey || event.metaKey)) return;
      if (event.key.toLowerCase() === 'z' && !event.shiftKey) {
        event.preventDefault();
        session.undo();
      } else if (event.key.toLowerCase() === 'y' || (event.key.toLowerCase() === 'z' && event.shiftKey)) {
        event.preventDefault();
        session.redo();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [session]);

  async function openLoaded(file: OpenedPdf): Promise<void> {
    try {
      await session.openPdf(file.name, file.bytes);
      pathRef.current = file.nativePath;
      setStatus(null);
    } catch (error: unknown) {
      setStatus(error instanceof Error ? error.message : 'Could not open that PDF');
    }
  }

  function ensureAdapter(): FileAdapter | null {
    const input = inputRef.current;
    if (!input) return null;
    adapterRef.current ??= createFileAdapter(input);
    return adapterRef.current;
  }

  async function save(): Promise<boolean> {
    const adapter = ensureAdapter();
    if (!adapter || !view.hasDocument) return false;
    try {
      const built = await session.buildSavedPdf();
      const stored = await adapter.savePdf({ ...built, nativePath: pathRef.current });
      if (!stored) return false;
      session.commitSave(built.bytes, stored.name);
      pathRef.current = stored.nativePath;
      setStatus(`Saved ${stored.name}`);
      return true;
    } catch (error: unknown) {
      setStatus(error instanceof Error ? error.message : 'Could not save');
      return false;
    }
  }

  return (
    <div className="app">
      <input
        ref={inputRef}
        className="file-input"
        type="file"
        accept="application/pdf,.pdf"
        aria-hidden="true"
        tabIndex={-1}
      />
      <Toolbar
        modules={modules}
        session={session}
        view={view}
        recentPens={recentPens}
        onRecentPens={setRecentPens}
        onOpen={() => {
          const adapter = ensureAdapter();
          if (!adapter) return;
          void adapter.openPdf().then((file) => {
            if (file) void openLoaded(file);
          });
        }}
        onNewNote={() => {
          pathRef.current = undefined;
          void session.newNote().catch((error: unknown) => {
            setStatus(error instanceof Error ? error.message : 'Could not start a note');
          });
        }}
        onSave={() => {
          void save();
        }}
        onClose={() => {
          void save().then((saved) => {
            if (!saved) return;
            session.clear();
            pathRef.current = undefined;
          });
        }}
      />
      <InkView session={session} view={view} gestures={gestures} onError={setStatus} />
      <p className="status" role="status">
        {status ?? (view.hasDocument ? view.fileName || 'Untitled note' : 'No document')}
      </p>
    </div>
  );
}
