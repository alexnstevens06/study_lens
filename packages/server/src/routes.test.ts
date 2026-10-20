import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs';
import { request, type Server } from 'node:http';
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

function get(
  port: number,
  path: string,
  headers: Record<string, string> = {},
): Promise<{ status: number; body: string; type: string }> {
  return new Promise((resolve, reject) => {
    const req = request({ hostname: '127.0.0.1', port, path, headers }, (response) => {
      const chunks: Buffer[] = [];
      response.on('data', (chunk: Buffer) => chunks.push(chunk));
      response.on('end', () => {
        resolve({
          status: response.statusCode ?? 0,
          body: Buffer.concat(chunks).toString('utf8'),
          type: String(response.headers['content-type'] ?? ''),
        });
      });
    });
    req.on('error', reject);
    req.end();
  });
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

    const browserHeader = await get(port, '/', {
      accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    });
    expect(browserHeader.type).toContain('text/html');
    const jsonPreferred = await get(port, '/', { accept: 'text/html;q=0.1, application/json' });
    expect(jsonPreferred.status).toBe(200);
    expect(jsonPreferred.type).toContain('application/json');
    expect(JSON.parse(jsonPreferred.body)).toEqual({ message: 'Study Partner Backend is running' });
    const htmlPreferred = await get(port, '/', { accept: 'application/json;q=0.2, text/html' });
    expect(htmlPreferred.type).toContain('text/html');
  });

  it('does not serve files outside the static directory', async () => {
    const parent = mkdtempSync(join(tmpdir(), 'study-lens-parent-'));
    const directory = join(parent, 'public');
    mkdirSync(directory);
    writeFileSync(join(directory, 'index.html'), '<!doctype html><title>Study Partner</title>');
    writeFileSync(join(parent, 'secret.txt'), 'secret');
    const port = await listen(options({ staticDir: directory }));
    const escaped = await get(port, '/%2e%2e%2fsecret.txt');
    expect(escaped.status).toBe(404);
    expect(escaped.body).not.toContain('secret');
    expect((await get(port, '/../secret.txt')).status).toBe(404);
    expect((await get(port, '/%')).status).toBe(404);
    const posted = await fetch(`http://127.0.0.1:${port}/prompts`, { method: 'POST' });
    expect(posted.status).toBe(405);
  });
});
