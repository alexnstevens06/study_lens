import type { FileAdapter, OpenedPdf } from '@study-lens/core';

function blobPart(bytes: Uint8Array): BlobPart {
  const copy = new Uint8Array(bytes.byteLength);
  copy.set(bytes);
  return copy;
}

export function createBrowserFileAdapter(input: HTMLInputElement): FileAdapter {
  let pending: ((file: OpenedPdf | null) => void) | null = null;
  input.addEventListener('change', () => {
    const file = input.files?.[0];
    input.value = '';
    const resolve = pending;
    pending = null;
    if (!resolve) return;
    if (!file) {
      resolve(null);
      return;
    }
    void file.arrayBuffer().then((buffer) => {
      resolve({ name: file.name, bytes: new Uint8Array(buffer) });
    });
  });

  return {
    openPdf() {
      return new Promise((resolve) => {
        pending?.(null);
        pending = resolve;
        input.click();
      });
    },
    async savePdf(file: OpenedPdf): Promise<OpenedPdf> {
      const url = URL.createObjectURL(new Blob([blobPart(file.bytes)], { type: 'application/pdf' }));
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = file.name;
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1500);
      return { name: file.name, bytes: file.bytes };
    },
  };
}
