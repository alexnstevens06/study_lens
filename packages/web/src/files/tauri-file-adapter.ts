import { open, save } from '@tauri-apps/plugin-dialog';
import { readFile, writeFile } from '@tauri-apps/plugin-fs';
import type { FileAdapter, OpenedPdf } from '@study-lens/core';

function fileName(path: string, fallback: string): string {
  return path.split(/[/\\]/).pop() || fallback;
}

export function createTauriFileAdapter(): FileAdapter {
  return {
    async openPdf(): Promise<OpenedPdf | null> {
      const selected = await open({
        multiple: false,
        filters: [{ name: 'PDF', extensions: ['pdf'] }],
      });
      if (typeof selected !== 'string') return null;
      const bytes = await readFile(selected);
      return { name: fileName(selected, 'document.pdf'), bytes, nativePath: selected };
    },
    async savePdf(file: OpenedPdf): Promise<OpenedPdf | null> {
      const target =
        file.nativePath ??
        (await save({
          defaultPath: file.name,
          filters: [{ name: 'PDF', extensions: ['pdf'] }],
        }));
      if (typeof target !== 'string') return null;
      await writeFile(target, file.bytes);
      return { name: fileName(target, file.name), bytes: file.bytes, nativePath: target };
    },
  };
}
