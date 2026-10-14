import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { enabledGestures, enabledModules, parseConfig } from './config.js';
import { classifySwipe, resolvePointerAction } from './pointer.js';
import { DEFAULT_PEN, rememberPen } from './types.js';

const legacyConfigPath = join(dirname(fileURLToPath(import.meta.url)), '../../../legacy/config.json');

describe('config loading', () => {
  it('loads the legacy Python config and orders modules by priority', () => {
    const config = parseConfig(JSON.parse(readFileSync(legacyConfigPath, 'utf8')));
    expect(enabledModules(config).map((module) => module.id)).toEqual([
      'open-pdf',
      'navigation',
      'undo-redo',
      'new-note',
      'save',
      'pen-settings',
      'close-pdf',
    ]);
    expect(enabledGestures(config)).toEqual(new Set(['pinch', 'swipe', 'pen', 'pan', 'clipboard']));
  });

  it('skips disabled modules and gestures', () => {
    const config = parseConfig({
      modules: { 'open-pdf': true, 'close-pdf': false, save: true },
      gestures: { pen: true, swipe: false },
    });
    expect(enabledModules(config).map((module) => module.id)).toEqual(['open-pdf', 'save']);
    expect([...enabledGestures(config)]).toEqual(['pen']);
  });

  it('rejects a non-boolean flag', () => {
    expect(() => parseConfig({ modules: { 'open-pdf': 'yes' } })).toThrow(/true or false/);
  });

  it('keeps six recent pens with the newest first', () => {
    let recent = [DEFAULT_PEN];
    for (let width = 3; width <= 8; width += 1) {
      recent = rememberPen(recent, { ...DEFAULT_PEN, width });
    }
    expect(recent.map((pen) => pen.width)).toEqual([8, 7, 6, 5, 4, 3]);
    recent = rememberPen(recent, { ...DEFAULT_PEN, width: 5 });
    expect(recent.map((pen) => pen.width)).toEqual([5, 8, 7, 6, 4, 3]);
  });
});

describe('stylus tool switching', () => {
  it('maps the eraser end to the eraser and the pen tip to the pencil', () => {
    expect(
      resolvePointerAction({ kind: 'pen', button: 5, buttons: 32, activeTool: 'pencil', penEnabled: true }),
    ).toEqual({ type: 'draw', tool: 'eraser', stick: true });
    expect(
      resolvePointerAction({ kind: 'pen', button: 0, buttons: 1, activeTool: 'eraser', penEnabled: true }),
    ).toEqual({ type: 'draw', tool: 'pencil', stick: true });
    expect(
      resolvePointerAction({ kind: 'pen', button: 2, buttons: 2, activeTool: 'pencil', penEnabled: true }),
    ).toEqual({ type: 'draw', tool: 'lasso', stick: true });
  });

  it('turns a fast horizontal finger swipe into a page change', () => {
    expect(classifySwipe(-80, 4, 180)).toBe('next');
    expect(classifySwipe(90, -10, 200)).toBe('previous');
    expect(classifySwipe(-80, 4, 900)).toBeNull();
    expect(classifySwipe(-10, 80, 120)).toBeNull();
  });
});
