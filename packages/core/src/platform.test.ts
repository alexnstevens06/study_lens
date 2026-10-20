import { describe, expect, it } from 'vitest';
import {
  AllFeaturesEntitled,
  FEATURE_FLAGS,
  MemoryContextStore,
  MemoryDocumentStore,
  SingleUserAuth,
} from './platform.js';

describe('local platform seams', () => {
  it('keeps one user from reading another user context or documents', async () => {
    const contexts = new MemoryContextStore();
    await contexts.add('local', { type: 'text', content: 'mine', metadata: { page: 1 } });
    await contexts.add('other', { type: 'text', content: 'theirs', metadata: {} });
    const listed = await contexts.list('local');
    expect(listed).toEqual([{ type: 'text', content: 'mine', metadata: { page: 1 } }]);
    const first = listed[0];
    if (!first) throw new Error('missing context');
    first.metadata.page = 9;
    expect((await contexts.list('local'))[0]?.metadata.page).toBe(1);

    const documents = new MemoryDocumentStore();
    await documents.write('a', 'b/c', new Uint8Array([1]));
    await documents.write('a/b', 'c', new Uint8Array([2]));
    const stored = await documents.read('a', 'b/c');
    expect(stored).toEqual(new Uint8Array([1]));
    expect(await documents.read('a/b', 'c')).toEqual(new Uint8Array([2]));
    if (!stored) throw new Error('missing document');
    stored[0] = 9;
    expect((await documents.read('a', 'b/c'))?.[0]).toBe(1);
  });

  it('enables every current feature for the single local user', async () => {
    const session = await new SingleUserAuth().getSession();
    const entitlements = new AllFeaturesEntitled();
    for (const flag of FEATURE_FLAGS) {
      expect(await entitlements.isEnabled(flag, session)).toBe(true);
    }
  });
});
