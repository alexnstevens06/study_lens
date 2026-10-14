import { mkdtempSync, writeFileSync } from 'node:fs';
import type { Server } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach, describe, expect, it } from 'vitest';
import { AllFeaturesEntitled, MemoryContextStore, type AuthProvider, type EntitlementService, type UserSession } from '@study-lens/core';
import { createStudyServer, type ServerOptions } from './app.js';

const servers: Server[] = [];

afterEach(async () => {
  await Promise.all(servers.splice(0).map((server) => new Promise<void>((resolve) => server.close(() => resolve()))));
});

function options(overrides: Partial<ServerOptions> = {}): ServerOptions {
  const directory = mkdtempSync(join(tmpdir(), 'study-lens-'));
  const promptsFile = join(directory, 'prompts.json');
  writeFileSync(promptsFile, JSON.stringify({ system_prompt: 'Study.', summarize_prompt: 'Summarize.' }));
  return {
    auth: { async getSession() { return { userId: 'local' }; } },
    entitlements: new AllFeaturesEntitled(),
    contexts: new MemoryContextStore(),
    promptsFile,
    configFile: null,
    staticDir: null,
    ...overrides,
  };
}

async function listen(serverOptions: ServerOptions): Promise<number> {
  const server = createStudyServer(serverOptions);
  servers.push(server);
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  if (!address || typeof address === 'string') throw new Error('No port');
  return address.port;
}

describe('API routes', () => {
  it('serves the root message, context, and prompts', async () => {
    const port = await listen(options());
    const root = await fetch(`http://127.0.0.1:${port}/`);
    expect(await root.json()).toEqual({ message: 'Study Partner Backend is running' });

    const created = await fetch(`http://127.0.0.1:${port}/context`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ type: 'text', content: 'Page 12', metadata: { page: 12 } }),
    });
    expect(created.status).toBe(200);
    expect(await created.json()).toEqual({ message: 'Context added' });

    const listed = await fetch(`http://127.0.0.1:${port}/context`);
    expect(await listed.json()).toEqual([{ type: 'text', content: 'Page 12', metadata: { page: 12 } }]);

    const prompts = await fetch(`http://127.0.0.1:${port}/prompts`);
    expect(await prompts.json()).toEqual({ system_prompt: 'Study.', summarize_prompt: 'Summarize.' });

    const cleared = await fetch(`http://127.0.0.1:${port}/context`, { method: 'DELETE' });
    expect(await cleared.json()).toEqual({ message: 'Context cleared' });
    expect(await (await fetch(`http://127.0.0.1:${port}/context`)).json()).toEqual([]);

    const bad = await fetch(`http://127.0.0.1:${port}/context`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ content: 'missing type' }),
    });
    expect(bad.status).toBe(400);
    const malformed = await fetch(`http://127.0.0.1:${port}/context`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: '{',
    });
    expect(malformed.status).toBe(400);
  });

  it('rejects a signed-out client and a disabled feature', async () => {
    const denying: EntitlementService = {
      async isEnabled() {
        return false;
      },
    };
    const port = await listen(options({ entitlements: denying }));
    const bad = await fetch(`http://127.0.0.1:${port}/context`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ content: 'missing type' }),
    });
    expect(bad.status).toBe(403);

    const signedOut: AuthProvider = {
      async getSession(): Promise<UserSession | null> {
        return null;
      },
    };
    const closed = await listen(options({ auth: signedOut }));
    const denied = await fetch(`http://127.0.0.1:${closed}/prompts`);
    expect(denied.status).toBe(401);
  });

  it('returns the app shell for browsers and JSON for API clients', async () => {
    const directory = mkdtempSync(join(tmpdir(), 'study-lens-static-'));
    writeFileSync(join(directory, 'index.html'), '<!doctype html><title>Study Partner</title>');
    const port = await listen(options({ staticDir: directory }));
    const browser = await fetch(`http://127.0.0.1:${port}/`, { headers: { accept: 'text/html' } });
    expect(browser.headers.get('content-type')).toContain('text/html');
    expect(await browser.text()).toContain('Study Partner');
    const client = await fetch(`http://127.0.0.1:${port}/`, { headers: { accept: 'application/json' } });
    expect(await client.json()).toEqual({ message: 'Study Partner Backend is running' });
  });
});
