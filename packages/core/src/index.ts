export { assertNever } from './assert-never.js';
export { bakeAnnotations, countPageImages, listInkAnnotations, type InkAnnotationRecord } from './annotations.js';
export { UndoManager, applyCommand, type Command, type HistoryDirection } from './commands.js';
export {
  GESTURES,
  MODULES,
  enabledGestures,
  enabledModules,
  isRecord,
  parseConfig,
  type AppConfig,
  type GestureDescriptor,
  type GestureId,
  type ModuleDescriptor,
  type ModuleId,
} from './config.js';
export {
  ERASER_REACH,
  pointInPolygon,
  rectIntersectsPolygon,
  strokeHitsEraser,
  strokeIntersectsPolygon,
  type Rect,
} from './geometry.js';
export { PageCache } from './page-cache.js';
export { PageModel, type DrawnImage, type DrawnStroke, type RenderState } from './page-model.js';
export {
  A4_HEIGHT,
  A4_WIDTH,
  appendMatchingPage,
  createBlankPdf,
  noteFileName,
  readPdfStructure,
  type PageSize,
} from './pdf-document.js';
export {
  AllFeaturesEntitled,
  FEATURE_FLAGS,
  MemoryContextStore,
  MemoryDocumentStore,
  SingleUserAuth,
  type AuthProvider,
  type ContextItem,
  type ContextStore,
  type DocumentStore,
  type EntitlementService,
  type FeatureFlag,
  type FileAdapter,
  type OpenedPdf,
  type UserSession,
} from './platform.js';
export {
  MAX_VIEW_ZOOM,
  MIN_VIEW_ZOOM,
  classifySwipe,
  nextViewZoom,
  parsePageNumber,
  pointerKind,
  resolvePointerAction,
  type PointerAction,
  type PointerKind,
} from './pointer.js';
export { StudySession, type SavedPdf, type SessionView } from './session.js';
export {
  DEFAULT_PEN,
  RENDER_SCALE,
  RECENT_PEN_LIMIT,
  cloneImage,
  clonePen,
  cloneSnapshot,
  cloneStroke,
  cssColor,
  emptyPage,
  newId,
  normalizePressure,
  pressureWidth,
  rememberPen,
  samePen,
  type ItemMove,
  type PageSnapshot,
  type PenSettings,
  type PlacedImage,
  type Point,
  type Rgba,
  type Stroke,
  type Tool,
} from './types.js';
