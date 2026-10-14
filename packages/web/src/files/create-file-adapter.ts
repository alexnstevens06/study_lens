import type { FileAdapter } from '@study-lens/core';
import { createBrowserFileAdapter } from './browser-file-adapter';
import { createTauriFileAdapter } from './tauri-file-adapter';

export function isTauri(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

export function createFileAdapter(input: HTMLInputElement): FileAdapter {
  if (isTauri()) return createTauriFileAdapter();
  return createBrowserFileAdapter(input);
}
