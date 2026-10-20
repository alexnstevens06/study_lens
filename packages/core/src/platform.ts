export interface UserSession {
  userId: string;
}

/**
 * Replace this for real accounts. The default always represents the one
 * person using a self-hosted or desktop copy.
 */
export interface AuthProvider {
  getSession(): Promise<UserSession | null>;
}

export class SingleUserAuth implements AuthProvider {
  async getSession(): Promise<UserSession> {
    return { userId: 'local' };
  }
}

export const FEATURE_FLAGS = ['annotations', 'context', 'prompts'] as const;
export type FeatureFlag = (typeof FEATURE_FLAGS)[number];

/**
 * Replace this when a free tier and a bundle subscription exist.
 * The default enables every current feature.
 */
export interface EntitlementService {
  isEnabled(flag: FeatureFlag, session: UserSession): Promise<boolean>;
}

export class AllFeaturesEntitled implements EntitlementService {
  async isEnabled(_flag: FeatureFlag, _session: UserSession): Promise<boolean> {
    return true;
  }
}

export interface ContextItem {
  type: string;
  content: string;
  metadata: Record<string, unknown>;
}

/** Study context, partitioned by user id so a later account system can store rows per person. */
export interface ContextStore {
  list(userId: string): Promise<ContextItem[]>;
  add(userId: string, item: ContextItem): Promise<void>;
  clear(userId: string): Promise<void>;
}

export class MemoryContextStore implements ContextStore {
  private readonly byUser = new Map<string, ContextItem[]>();

  async list(userId: string): Promise<ContextItem[]> {
    return (this.byUser.get(userId) ?? []).map((item) => ({
      ...item,
      metadata: { ...item.metadata },
    }));
  }

  async add(userId: string, item: ContextItem): Promise<void> {
    const items = this.byUser.get(userId) ?? [];
    items.push({ ...item, metadata: { ...item.metadata } });
    this.byUser.set(userId, items);
  }

  async clear(userId: string): Promise<void> {
    this.byUser.set(userId, []);
  }
}

/** Document bytes behind a storage interface. The app keeps the open file in memory today. */
export interface DocumentStore {
  read(userId: string, documentId: string): Promise<Uint8Array | null>;
  write(userId: string, documentId: string, bytes: Uint8Array): Promise<void>;
}

export class MemoryDocumentStore implements DocumentStore {
  private readonly data = new Map<string, Uint8Array>();

  async read(userId: string, documentId: string): Promise<Uint8Array | null> {
    const bytes = this.data.get(this.key(userId, documentId));
    return bytes ? bytes.slice() : null;
  }

  async write(userId: string, documentId: string, bytes: Uint8Array): Promise<void> {
    this.data.set(this.key(userId, documentId), bytes.slice());
  }

  /** Length-prefix the user id so a slash inside either id cannot collide. */
  private key(userId: string, documentId: string): string {
    return `${userId.length}:${userId}\u0000${documentId}`;
  }
}

export interface OpenedPdf {
  name: string;
  bytes: Uint8Array;
  nativePath?: string;
}

/** Web uses browser file inputs. Desktop uses native dialogs behind the same calls. */
export interface FileAdapter {
  openPdf(): Promise<OpenedPdf | null>;
  savePdf(file: OpenedPdf): Promise<OpenedPdf | null>;
}
