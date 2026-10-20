import { parseConfig, type AppConfig } from '@study-lens/core';
import bundled from '../../../config.json';

export async function loadAppConfig(): Promise<AppConfig> {
  try {
    const response = await fetch('/config.json');
    if (response.ok) return parseConfig(await response.json());
  } catch {
    // Desktop builds and offline dev fall back to the file copied at build time.
  }
  return parseConfig(bundled);
}
