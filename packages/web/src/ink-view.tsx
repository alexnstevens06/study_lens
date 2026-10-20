import {
  MIN_VIEW_ZOOM,
  RENDER_SCALE,
  classifySwipe,
  drawingPressure,
  newId,
  nextViewZoom,
  pointerKind,
  resolvePointerAction,
  type GestureId,
  type SessionView,
  type StudySession,
} from '@study-lens/core';
import { useEffect, useRef, useState, type ReactElement } from 'react';
import { drawScene } from './draw';
import { renderPdfPage } from './pdf-render';

interface InkViewProps {
  session: StudySession;
  view: SessionView;
  gestures: Set<GestureId>;
  onError: (message: string) => void;
}

interface Pan {
  x: number;
  y: number;
}

export function InkView(props: InkViewProps): ReactElement {
  const { session, view } = props;
  const viewportRef = useRef<HTMLDivElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);
  const pdfRef = useRef<HTMLCanvasElement>(null);
  const inkRef = useRef<HTMLCanvasElement>(null);
  const renderKey = view.hasDocument ? `${view.documentGeneration}:${view.pageIndex}` : '';
  const [paintedKey, setPaintedKey] = useState<string | null>(null);
  if (paintedKey !== null && paintedKey !== renderKey) setPaintedKey(null);
  const ready = renderKey.length > 0 && paintedKey === renderKey;
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<Pan>({ x: 24, y: 24 });
  const gesturesRef = useRef(props.gestures);
  const errorRef = useRef(props.onError);
  const toolRef = useRef(view.tool);
  const zoomRef = useRef(zoom);
  const panRef = useRef(pan);
  gesturesRef.current = props.gestures;
  errorRef.current = props.onError;
  toolRef.current = view.tool;
  zoomRef.current = zoom;
  panRef.current = pan;

  const pageWidth = view.pageWidth * RENDER_SCALE;
  const pageHeight = view.pageHeight * RENDER_SCALE;

  useEffect(() => {
    if (!view.hasDocument) return;
    const viewport = viewportRef.current;
    if (!viewport || pageWidth === 0 || pageHeight === 0) return;
    const fitted = Math.min((viewport.clientWidth - 48) / pageWidth, (viewport.clientHeight - 48) / pageHeight, 1.5);
    const next = Math.max(MIN_VIEW_ZOOM, fitted);
    const nextPan = {
      x: (viewport.clientWidth - pageWidth * next) / 2,
      y: Math.max(16, (viewport.clientHeight - pageHeight * next) / 2),
    };
    zoomRef.current = next;
    panRef.current = nextPan;
    setZoom(next);
    setPan(nextPan);
  }, [view.documentGeneration, view.hasDocument, pageWidth, pageHeight]);

  useEffect(() => {
    const canvas = pdfRef.current;
    const bytes = session.documentBytes;
    if (!canvas || !bytes || renderKey.length === 0) return;
    let cancelled = false;
    void renderPdfPage(bytes, view.pageIndex, canvas, RENDER_SCALE)
      .then(() => {
        if (!cancelled) setPaintedKey(renderKey);
      })
      .catch((error: unknown) => {
        if (!cancelled) errorRef.current(error instanceof Error ? error.message : 'Could not render the page');
      });
    return () => {
      cancelled = true;
    };
  }, [session, renderKey, view.pageIndex]);

  useEffect(() => {
    const paint = (): void => {
      const canvas = inkRef.current;
      if (!canvas || !view.hasDocument) return;
      drawScene(canvas, session.page.getRenderState(), pageWidth, pageHeight, paint);
    };
    paint();
    return session.subscribeInk(paint);
  }, [session, view.hasDocument, view.documentGeneration, pageWidth, pageHeight]);

  useEffect(() => {
    let frame = 0;
    let running = false;
    let last = performance.now();
    const loop = (now: number): void => {
      const elapsed = now - last;
      last = now;
      const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      const still = session.stepFade(reduced ? 1 : elapsed / 300);
      if (still) frame = requestAnimationFrame(loop);
      else running = false;
    };
    const start = (): void => {
      if (running || !session.page.hasFade()) return;
      running = true;
      last = performance.now();
      frame = requestAnimationFrame(loop);
    };
    start();
    const unsubscribe = session.subscribeInk(start);
    return () => {
      unsubscribe();
      cancelAnimationFrame(frame);
    };
  }, [session]);

  useEffect(() => {
    const viewport = viewportRef.current;
    const page = pageRef.current;
    if (!viewport || !page || !view.hasDocument) return;

    const touches = new Map<number, { x: number; y: number }>();
    let drawingId: number | null = null;
    let mousePan: { x: number; y: number } | null = null;
    let spaceDown = false;
    let pinchDistance = 0;
    let swipe: { x: number; y: number; time: number; pan: Pan } | null = null;
    let holdTimer = 0;
    let held = false;

    const toPage = (event: PointerEvent): { x: number; y: number } | null => {
      const rect = page.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return null;
      return {
        x: ((event.clientX - rect.left) / rect.width) * page.offsetWidth,
        y: ((event.clientY - rect.top) / rect.height) * page.offsetHeight,
      };
    };

    const setView = (nextZoom: number, nextPan: Pan): void => {
      zoomRef.current = nextZoom;
      panRef.current = nextPan;
      setZoom(nextZoom);
      setPan(nextPan);
    };

    const zoomAt = (clientX: number, clientY: number, factor: number): void => {
      const current = zoomRef.current;
      const next = nextViewZoom(current, factor);
      const rect = viewport.getBoundingClientRect();
      const px = clientX - rect.left;
      const py = clientY - rect.top;
      const origin = panRef.current;
      const pageX = (px - origin.x) / current;
      const pageY = (py - origin.y) / current;
      setView(next, { x: px - pageX * next, y: py - pageY * next });
    };

    const pasteAt = (point: { x: number; y: number }): void => {
      if (!gesturesRef.current.has('clipboard')) return;
      void navigator.clipboard
        .read()
        .then(async (items) => {
          for (const item of items) {
            const type = item.types.find((entry) => entry.startsWith('image/'));
            if (!type) continue;
            const blob = await item.getType(type);
            const bitmap = await createImageBitmap(blob);
            const surface = document.createElement('canvas');
            surface.width = bitmap.width;
            surface.height = bitmap.height;
            const context = surface.getContext('2d');
            if (!context) return;
            context.drawImage(bitmap, 0, 0);
            const png = await new Promise<Blob>((resolve, reject) => {
              surface.toBlob((value) => (value ? resolve(value) : reject(new Error('Could not read the clipboard image'))), 'image/png');
            });
            const bytes = new Uint8Array(await png.arrayBuffer());
            session.pasteImage({
              id: newId(),
              bytes,
              mime: 'image/png',
              x: point.x - bitmap.width / 2,
              y: point.y - bitmap.height / 2,
              width: bitmap.width,
              height: bitmap.height,
              saved: false,
            });
            return;
          }
        })
        .catch((error: unknown) => {
          errorRef.current(error instanceof Error ? error.message : 'Clipboard image is unavailable');
        });
    };

    const onPointerDown = (event: PointerEvent): void => {
      const kind = pointerKind(event.pointerType);
      if (kind === 'touch') {
        touches.set(event.pointerId, { x: event.clientX, y: event.clientY });
        held = false;
        window.clearTimeout(holdTimer);
        if (touches.size === 1) {
          swipe = { x: event.clientX, y: event.clientY, time: performance.now(), pan: { ...panRef.current } };
          const point = toPage(event);
          if (point && gesturesRef.current.has('clipboard')) {
            holdTimer = window.setTimeout(() => {
              held = true;
              pasteAt(point);
            }, 600);
          }
        }
        if (touches.size === 2 && gesturesRef.current.has('pinch')) {
          const [a, b] = [...touches.values()];
          if (a && b) pinchDistance = Math.hypot(a.x - b.x, a.y - b.y);
        }
        return;
      }
      if ((spaceDown || event.button === 1) && gesturesRef.current.has('pan')) {
        mousePan = { x: event.clientX, y: event.clientY };
        viewport.setPointerCapture(event.pointerId);
        return;
      }
      const action = resolvePointerAction({
        kind,
        button: event.button,
        buttons: event.buttons,
        activeTool: toolRef.current,
        penEnabled: gesturesRef.current.has('pen'),
      });
      if (action.type !== 'draw') return;
      const point = toPage(event);
      if (!point) return;
      event.preventDefault();
      if (action.stick) session.setTool(action.tool);
      drawingId = event.pointerId;
      viewport.setPointerCapture(event.pointerId);
      session.pointerDown(action.tool, point.x, point.y, drawingPressure(kind, event.pressure));
    };

    const onPointerMove = (event: PointerEvent): void => {
      if (drawingId === event.pointerId) {
        const point = toPage(event);
        if (point) {
          session.pointerMove(point.x, point.y, drawingPressure(pointerKind(event.pointerType), event.pressure));
        }
        return;
      }
      if (mousePan && gesturesRef.current.has('pan')) {
        const next = {
          x: panRef.current.x + event.clientX - mousePan.x,
          y: panRef.current.y + event.clientY - mousePan.y,
        };
        mousePan = { x: event.clientX, y: event.clientY };
        panRef.current = next;
        setPan(next);
        return;
      }
      if (!touches.has(event.pointerId)) return;
      const previous = touches.get(event.pointerId);
      touches.set(event.pointerId, { x: event.clientX, y: event.clientY });
      if (previous && Math.hypot(event.clientX - previous.x, event.clientY - previous.y) > 8) {
        window.clearTimeout(holdTimer);
      }
      if (touches.size === 2 && gesturesRef.current.has('pinch') && pinchDistance > 0) {
        const [a, b] = [...touches.values()];
        if (!a || !b) return;
        const distance = Math.hypot(a.x - b.x, a.y - b.y);
        zoomAt((a.x + b.x) / 2, (a.y + b.y) / 2, distance / pinchDistance);
        pinchDistance = distance;
        return;
      }
      if (touches.size === 1 && previous && gesturesRef.current.has('pan')) {
        const next = {
          x: panRef.current.x + event.clientX - previous.x,
          y: panRef.current.y + event.clientY - previous.y,
        };
        panRef.current = next;
        setPan(next);
      }
    };

    const onPointerUp = (event: PointerEvent): void => {
      window.clearTimeout(holdTimer);
      if (drawingId === event.pointerId) {
        const point = toPage(event);
        if (point) {
          session.pointerUp(point.x, point.y, drawingPressure(pointerKind(event.pointerType), event.pressure));
        }
        drawingId = null;
        return;
      }
      if (mousePan) {
        mousePan = null;
        return;
      }
      const wasTouch = touches.delete(event.pointerId);
      if (!wasTouch || touches.size > 0 || !swipe || held) {
        if (touches.size < 2) pinchDistance = 0;
        return;
      }
      const dx = event.clientX - swipe.x;
      const dy = event.clientY - swipe.y;
      const direction = gesturesRef.current.has('swipe')
        ? classifySwipe(dx, dy, performance.now() - swipe.time)
        : null;
      if (direction) {
        panRef.current = swipe.pan;
        setPan(swipe.pan);
        void session.changePage(direction === 'next' ? 1 : -1);
      }
      swipe = null;
      pinchDistance = 0;
    };

    const onWheel = (event: WheelEvent): void => {
      if (!gesturesRef.current.has('pinch')) return;
      event.preventDefault();
      zoomAt(event.clientX, event.clientY, event.deltaY < 0 ? 1.08 : 1 / 1.08);
    };

    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.code === 'Space') spaceDown = true;
    };
    const onKeyUp = (event: KeyboardEvent): void => {
      if (event.code === 'Space') spaceDown = false;
    };
    const onContextMenu = (event: Event): void => event.preventDefault();

    viewport.addEventListener('pointerdown', onPointerDown);
    viewport.addEventListener('pointermove', onPointerMove);
    viewport.addEventListener('pointerup', onPointerUp);
    viewport.addEventListener('pointercancel', onPointerUp);
    viewport.addEventListener('wheel', onWheel, { passive: false });
    viewport.addEventListener('contextmenu', onContextMenu);
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('keyup', onKeyUp);
    return () => {
      window.clearTimeout(holdTimer);
      viewport.removeEventListener('pointerdown', onPointerDown);
      viewport.removeEventListener('pointermove', onPointerMove);
      viewport.removeEventListener('pointerup', onPointerUp);
      viewport.removeEventListener('pointercancel', onPointerUp);
      viewport.removeEventListener('wheel', onWheel);
      viewport.removeEventListener('contextmenu', onContextMenu);
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('keyup', onKeyUp);
    };
  }, [session, view.hasDocument]);

  return (
    <div className="desk" ref={viewportRef}>
      {view.hasDocument ? (
        <div
          ref={pageRef}
          className="page-stage"
          data-testid="ink-surface"
          data-ready={ready ? 'true' : 'false'}
          data-stroke-count={view.strokeCount}
          data-document-generation={view.documentGeneration}
          style={{
            width: pageWidth,
            height: pageHeight,
            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
          }}
        >
          <canvas ref={pdfRef} className="pdf-canvas" />
          <canvas ref={inkRef} className="ink-canvas" />
        </div>
      ) : (
        <p className="empty">Open a PDF or start a new note.</p>
      )}
    </div>
  );
}
