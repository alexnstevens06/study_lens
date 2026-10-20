export type ModuleId =
  | 'open-pdf'
  | 'close-pdf'
  | 'navigation'
  | 'new-note'
  | 'pen-settings'
  | 'undo-redo'
  | 'save';

export type GestureId = 'pinch' | 'swipe' | 'pen' | 'pan' | 'clipboard';

export interface ModuleDescriptor {
  id: ModuleId;
  priority: number;
  legacyPaths: string[];
}

export interface GestureDescriptor {
  id: GestureId;
  legacyPaths: string[];
}

export interface AppConfig {
  modules: Record<string, boolean>;
  gestures: Record<string, boolean>;
}

export const MODULES: ModuleDescriptor[] = [
  { id: 'open-pdf', priority: 5, legacyPaths: ['src/frontend/modules/open_pdf_module.py'] },
  { id: 'navigation', priority: 10, legacyPaths: ['src/frontend/modules/navigation_module.py'] },
  { id: 'undo-redo', priority: 10, legacyPaths: ['src/frontend/modules/undo_redo_module.py'] },
  { id: 'new-note', priority: 20, legacyPaths: ['src/frontend/modules/new_note_module.py'] },
  { id: 'save', priority: 20, legacyPaths: ['src/frontend/modules/save_module.py'] },
  { id: 'pen-settings', priority: 40, legacyPaths: ['src/frontend/modules/pen_settings_module.py'] },
  { id: 'close-pdf', priority: 50, legacyPaths: ['src/frontend/modules/close_pdf_module.py'] },
];

export const GESTURES: GestureDescriptor[] = [
  { id: 'pinch', legacyPaths: ['src/frontend/gestures/pinch_gesture.py'] },
  { id: 'swipe', legacyPaths: ['src/frontend/gestures/swipe_gesture.py'] },
  { id: 'pen', legacyPaths: ['src/frontend/gestures/pen_gesture.py'] },
  { id: 'pan', legacyPaths: ['src/frontend/gestures/pan_gesture.py'] },
  { id: 'clipboard', legacyPaths: ['src/frontend/gestures/clipboard_handler.py'] },
];

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function booleanMap(value: unknown, label: string): Record<string, boolean> {
  if (value === undefined) return {};
  if (!isRecord(value)) throw new Error(`${label} must be an object`);
  const map: Record<string, boolean> = {};
  for (const [key, enabled] of Object.entries(value)) {
    if (typeof enabled !== 'boolean') throw new Error(`${label}.${key} must be true or false`);
    map[key] = enabled;
  }
  return map;
}

export function parseConfig(value: unknown): AppConfig {
  if (!isRecord(value)) throw new Error('Config must be an object');
  return {
    modules: booleanMap(value.modules, 'modules'),
    gestures: booleanMap(value.gestures, 'gestures'),
  };
}

function flagEnabled(map: Record<string, boolean>, id: string, legacyPaths: string[]): boolean {
  if (Object.prototype.hasOwnProperty.call(map, id)) return map[id] === true;
  for (const path of legacyPaths) {
    if (Object.prototype.hasOwnProperty.call(map, path)) return map[path] === true;
  }
  return false;
}

function configRank(order: string[], id: string, legacyPaths: string[]): number {
  const idIndex = order.indexOf(id);
  if (idIndex !== -1) return idIndex;
  let best = Number.POSITIVE_INFINITY;
  for (const path of legacyPaths) {
    const index = order.indexOf(path);
    if (index !== -1) best = Math.min(best, index);
  }
  return best;
}

/** Enabled modules, lowest priority first. Equal priorities keep config order. */
export function enabledModules(config: AppConfig): ModuleDescriptor[] {
  const order = Object.keys(config.modules);
  return MODULES.filter((module) => flagEnabled(config.modules, module.id, module.legacyPaths))
    .map((module, index) => ({
      module,
      index,
      rank: configRank(order, module.id, module.legacyPaths),
    }))
    .sort((a, b) => a.module.priority - b.module.priority || a.rank - b.rank || a.index - b.index)
    .map((entry) => entry.module);
}

export function enabledGestures(config: AppConfig): Set<GestureId> {
  const enabled = new Set<GestureId>();
  for (const gesture of GESTURES) {
    if (flagEnabled(config.gestures, gesture.id, gesture.legacyPaths)) enabled.add(gesture.id);
  }
  return enabled;
}
