"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { api } from "@/lib/api";
import {
  ArrowDownTrayIcon,
  ArrowUturnLeftIcon,
  ArrowUturnRightIcon,
  PencilIcon,
  CursorArrowRaysIcon,
  PhotoIcon,
  MinusIcon,
  PlusIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";

type Point = { x: number; y: number };
type Stroke = { id: string; color: string; width: number; points: Point[] };
type TextItem = { id: string; x: number; y: number; text: string; color: string; size: number };
type ImageItem = { id: string; x: number; y: number; w: number; h: number; url: string };
type CursorPresence = { id: string; x: number; y: number; color: string; label: string; ts: number };

export type BoardState = {
  version: 1;
  strokes: Stroke[];
  texts: TextItem[];
  images: ImageItem[];
};

const DEFAULT_STATE: BoardState = { version: 1, strokes: [], texts: [], images: [] };

function normalizeState(s: BoardState | undefined): BoardState {
  const anyS = (s || {}) as Partial<BoardState> & {
    strokes?: unknown;
    texts?: unknown;
    images?: unknown;
  };
  return {
    version: 1,
    strokes: Array.isArray(anyS.strokes) ? (anyS.strokes as Stroke[]) : [],
    texts: Array.isArray(anyS.texts)
      ? (anyS.texts as Partial<TextItem>[]).map((t) => ({
          id: typeof t.id === "string" ? t.id : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
          x: typeof t.x === "number" ? t.x : 0,
          y: typeof t.y === "number" ? t.y : 0,
          text: typeof t.text === "string" ? t.text : "",
          color: typeof t.color === "string" ? t.color : "#1E3A8A",
          size: typeof t.size === "number" ? t.size : 24,
        }))
      : [],
    images: Array.isArray(anyS.images)
      ? (anyS.images as Partial<ImageItem>[]).map((im) => ({
          id: typeof im.id === "string" ? im.id : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
          x: typeof im.x === "number" ? im.x : 0,
          y: typeof im.y === "number" ? im.y : 0,
          w: typeof im.w === "number" ? im.w : 0.4,
          h: typeof im.h === "number" ? im.h : 0.3,
          url: typeof im.url === "string" ? im.url : "",
        }))
      : [],
  };
}

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

function canvasPoint(canvas: HTMLCanvasElement, clientX: number, clientY: number): Point {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (clientX - rect.left) / rect.width,
    y: (clientY - rect.top) / rect.height,
  };
}

type Camera = { x: number; y: number; zoom: number };

function screenToWorld(p: Point, cam: Camera): Point {
  return { x: cam.x + p.x / cam.zoom, y: cam.y + p.y / cam.zoom };
}

function worldToScreen(p: Point, cam: Camera): Point {
  return { x: (p.x - cam.x) * cam.zoom, y: (p.y - cam.y) * cam.zoom };
}

function cloneState(s: BoardState): BoardState {
  return JSON.parse(JSON.stringify(normalizeState(s))) as BoardState;
}

function textHit(t: TextItem, p: Point, r: number): boolean {
  const w = Math.max(t.text.length, 1) * t.size * 0.55;
  const h = t.size * 1.25;
  return p.x >= t.x - r && p.x <= t.x + w + r && p.y >= t.y - r && p.y <= t.y + h + r;
}

function imageHit(im: ImageItem, p: Point, r: number): boolean {
  return p.x >= im.x - r && p.x <= im.x + im.w + r && p.y >= im.y - r && p.y <= im.y + im.h + r;
}

function findImageAt(images: ImageItem[], p: Point): ImageItem | null {
  return (
    [...images].reverse().find((im) => p.x >= im.x && p.x <= im.x + im.w && p.y >= im.y && p.y <= im.y + im.h) ?? null
  );
}

type ResizeCorner = "nw" | "ne" | "sw" | "se";
const MIN_IMAGE_SIZE = 0.05;

function computeImageResize(
  corner: ResizeCorner,
  start: { x: number; y: number; w: number; h: number },
  p: Point
): { x: number; y: number; w: number; h: number } {
  let { x, y, w, h } = start;
  if (corner === "se") {
    w = Math.max(MIN_IMAGE_SIZE, p.x - x);
    h = Math.max(MIN_IMAGE_SIZE, p.y - y);
  } else if (corner === "nw") {
    const nx = Math.min(p.x, x + w - MIN_IMAGE_SIZE);
    const ny = Math.min(p.y, y + h - MIN_IMAGE_SIZE);
    w = x + w - nx;
    h = y + h - ny;
    x = nx;
    y = ny;
  } else if (corner === "ne") {
    const ny = Math.min(p.y, y + h - MIN_IMAGE_SIZE);
    w = Math.max(MIN_IMAGE_SIZE, p.x - x);
    h = y + h - ny;
    y = ny;
  } else if (corner === "sw") {
    const nx = Math.min(p.x, x + w - MIN_IMAGE_SIZE);
    w = x + w - nx;
    h = Math.max(MIN_IMAGE_SIZE, p.y - y);
    x = nx;
  }
  return { x, y, w, h };
}

function imageScreenStyle(im: ImageItem, cam: Camera): CSSProperties {
  const tl = worldToScreen({ x: im.x, y: im.y }, cam);
  const br = worldToScreen({ x: im.x + im.w, y: im.y + im.h }, cam);
  return {
    left: `${tl.x * 100}%`,
    top: `${tl.y * 100}%`,
    width: `${(br.x - tl.x) * 100}%`,
    height: `${(br.y - tl.y) * 100}%`,
  };
}

function applyErase(cur: BoardState, p: Point, r: number): BoardState {
  const r2 = r * r;
  const strokes = cur.strokes.filter(
    (st) => !st.points.some((pt) => (pt.x - p.x) ** 2 + (pt.y - p.y) ** 2 <= r2)
  );
  const texts = cur.texts.filter((t) => !textHit(t, p, r));
  const images = cur.images.filter((im) => !imageHit(im, p, r));
  return { ...cur, strokes, texts, images };
}

const MAX_HISTORY = 50;

function applyBoardOp(
  prev: BoardState,
  op: {
    op?: string;
    id?: unknown;
    color?: unknown;
    width?: unknown;
    p?: unknown;
    r?: unknown;
    item?: unknown;
    x?: unknown;
    y?: unknown;
    w?: unknown;
    h?: unknown;
    state?: unknown;
  }
): BoardState {
  const cur = normalizeState(prev);
  const t = op?.op;
  if (t === "set_state") {
    const st = op.state;
    if (!st || typeof st !== "object") return cur;
    return normalizeState(st as BoardState);
  }
  if (t === "clear") return { ...DEFAULT_STATE };
  if (t === "stroke_begin") {
    if (typeof op.id !== "string") return cur;
    const color = typeof op.color === "string" ? op.color : "#1E3A8A";
    const width = typeof op.width === "number" ? op.width : 3;
    const p = op.p as unknown;
    if (!p || typeof p !== "object") return cur;
    const pp = p as { x?: unknown; y?: unknown };
    if (typeof pp.x !== "number" || typeof pp.y !== "number") return cur;
    return { ...cur, strokes: [...cur.strokes, { id: op.id, color, width, points: [pp as Point] }] };
  }
  if (t === "stroke_point") {
    if (typeof op.id !== "string") return cur;
    const p = op.p as unknown;
    if (!p || typeof p !== "object") return cur;
    const pp = p as { x?: unknown; y?: unknown };
    if (typeof pp.x !== "number" || typeof pp.y !== "number") return cur;
    const strokes = cur.strokes.map((s) =>
      s.id === op.id ? { ...s, points: [...s.points, pp as Point] } : s
    );
    return { ...cur, strokes };
  }
  if (t === "text_add") {
    const it = op.item as unknown;
    if (!it || typeof it !== "object") return cur;
    const item = it as Partial<TextItem>;
    if (
      typeof item.x !== "number" ||
      typeof item.y !== "number" ||
      typeof item.text !== "string" ||
      typeof item.color !== "string" ||
      typeof item.size !== "number"
    )
      return cur;
    return { ...cur, texts: [...cur.texts, item as TextItem] };
  }
  if (t === "image_add") {
    const it = op.item as unknown;
    if (!it || typeof it !== "object") return cur;
    const item = it as Partial<ImageItem>;
    if (
      typeof item.x !== "number" ||
      typeof item.y !== "number" ||
      typeof item.w !== "number" ||
      typeof item.h !== "number" ||
      typeof item.url !== "string"
    )
      return cur;
    const id = typeof item.id === "string" ? item.id : "";
    if (id && cur.images.some((im) => im.id === id)) return cur;
    return { ...cur, images: [...cur.images, item as ImageItem] };
  }
  if (t === "image_move") {
    if (typeof op.id !== "string" || typeof op.x !== "number" || typeof op.y !== "number") return cur;
    const images = cur.images.map((im) => (im.id === op.id ? { ...im, x: op.x as number, y: op.y as number } : im));
    return { ...cur, images };
  }
  if (t === "image_update") {
    if (
      typeof op.id !== "string" ||
      typeof op.x !== "number" ||
      typeof op.y !== "number" ||
      typeof op.w !== "number" ||
      typeof op.h !== "number"
    )
      return cur;
    const images = cur.images.map((im) =>
      im.id === op.id
        ? {
            ...im,
            x: op.x as number,
            y: op.y as number,
            w: Math.max(MIN_IMAGE_SIZE, op.w as number),
            h: Math.max(MIN_IMAGE_SIZE, op.h as number),
          }
        : im
    );
    return { ...cur, images };
  }
  if (t === "erase") {
    const p = op.p as unknown;
    const r = op.r;
    if (!p || typeof p !== "object" || typeof r !== "number") return cur;
    const pp = p as { x?: unknown; y?: unknown };
    if (typeof pp.x !== "number" || typeof pp.y !== "number") return cur;
    return applyErase(cur, pp as Point, r);
  }
  return cur;
}

export default function Whiteboard({
  boardId,
  shareToken,
  authToken,
  initialState,
  readonly = false,
  fullscreen = false,
}: {
  boardId: number;
  shareToken?: string;
  authToken?: string;
  initialState?: BoardState;
  readonly?: boolean;
  fullscreen?: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [state, setState] = useState<BoardState>(normalizeState(initialState) || DEFAULT_STATE);
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  }, [state]);
  const [tool, setTool] = useState<"move" | "pen" | "erase" | "text" | "image">("pen");
  const [color, setColor] = useState("#1E3A8A");
  const [width, setWidth] = useState(3);
  const [textSize, setTextSize] = useState(24);
  const [status, setStatus] = useState<"offline" | "connecting" | "online">("offline");
  const [cam, setCam] = useState<Camera>({ x: -0.5, y: -0.5, zoom: 1 });
  const camRef = useRef(cam);
  useEffect(() => {
    camRef.current = cam;
  }, [cam]);
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);

  const historyPastRef = useRef<BoardState[]>([]);
  const historyFutureRef = useRef<BoardState[]>([]);
  const eraseHistoryPushedRef = useRef(false);
  const erasingRef = useRef(false);
  const uploadInFlightRef = useRef(false);

  const wsUrl = useMemo(() => api.boards.wsUrl(boardId, shareToken, authToken), [boardId, shareToken, authToken]);

  const wsRef = useRef<WebSocket | null>(null);
  const sendTimerRef = useRef<number | null>(null);
  const pendingPointRef = useRef<{ id: string; p: Point } | null>(null);

  const clientIdRef = useRef<string>("");
  const clientColorRef = useRef<string>("");
  const clientLabelRef = useRef<string>(shareToken ? "Гость" : "Вы");
  const [cursors, setCursors] = useState<Record<string, CursorPresence>>({});
  const cursorSendTimerRef = useRef<number | null>(null);
  const lastCursorRef = useRef<Point | null>(null);

  const sendOp = useCallback(
    (op: Record<string, unknown>) => {
      if (readonly) return;
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      ws.send(JSON.stringify({ type: "op", op }));
    },
    [readonly]
  );

  const syncHistoryFlags = useCallback(() => {
    setCanUndo(historyPastRef.current.length > 0);
    setCanRedo(historyFutureRef.current.length > 0);
  }, []);

  const pushHistory = useCallback(() => {
    if (readonly) return;
    historyPastRef.current = [...historyPastRef.current.slice(-(MAX_HISTORY - 1)), cloneState(stateRef.current)];
    historyFutureRef.current = [];
    syncHistoryFlags();
  }, [readonly, syncHistoryFlags]);

  const applyState = useCallback(
    (next: BoardState, broadcast: boolean) => {
      const normalized = normalizeState(next);
      setState(normalized);
      if (broadcast) sendOp({ op: "set_state", state: normalized });
    },
    [sendOp]
  );

  const undo = useCallback(() => {
    if (readonly || historyPastRef.current.length === 0) return;
    const prev = historyPastRef.current.pop()!;
    historyFutureRef.current.push(cloneState(stateRef.current));
    applyState(prev, true);
    syncHistoryFlags();
  }, [readonly, applyState, syncHistoryFlags]);

  const redo = useCallback(() => {
    if (readonly || historyFutureRef.current.length === 0) return;
    const next = historyFutureRef.current.pop()!;
    historyPastRef.current.push(cloneState(stateRef.current));
    applyState(next, true);
    syncHistoryFlags();
  }, [readonly, applyState, syncHistoryFlags]);

  useEffect(() => {
    if (!clientIdRef.current) {
      clientIdRef.current = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
    }
    if (!clientColorRef.current) {
      const palette = ["#10B981", "#2563EB", "#F59E0B", "#EF4444", "#8B5CF6", "#0EA5E9"];
      clientColorRef.current = palette[Math.floor(Math.random() * palette.length)];
    }
  }, []);

  const scheduleStrokePoint = useCallback(
    (id: string, p: Point) => {
      if (readonly) return;
      pendingPointRef.current = { id, p };
      if (sendTimerRef.current) return;
      sendTimerRef.current = window.setTimeout(() => {
        const pending = pendingPointRef.current;
        pendingPointRef.current = null;
        sendTimerRef.current = null;
        if (pending) sendOp({ op: "stroke_point", id: pending.id, p: pending.p });
      }, 50);
    },
    [readonly, sendOp]
  );

  const redraw = useCallback(
    async (s: BoardState) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      // HiDPI
      const dpr = window.devicePixelRatio || 1;
      const rect = canvas.getBoundingClientRect();
      const w = Math.max(1, Math.floor(rect.width * dpr));
      const h = Math.max(1, Math.floor(rect.height * dpr));
      if (canvas.width !== w || canvas.height !== h) {
        canvas.width = w;
        canvas.height = h;
      }

      ctx.setTransform(w, 0, 0, h, 0, 0);
      ctx.clearRect(0, 0, 1, 1);

      ctx.save();
      ctx.translate(-cam.x * cam.zoom, -cam.y * cam.zoom);
      ctx.scale(cam.zoom, cam.zoom);

      // grid (world units)
      const step = 0.1; // 10% of viewport in world coords
      const viewW = 1 / cam.zoom;
      const viewH = 1 / cam.zoom;
      const x0 = cam.x;
      const y0 = cam.y;
      const x1 = cam.x + viewW;
      const y1 = cam.y + viewH;
      const gx0 = Math.floor(x0 / step) * step;
      const gy0 = Math.floor(y0 / step) * step;
      ctx.strokeStyle = "rgba(15, 23, 42, 0.06)";
      ctx.lineWidth = (1 / w) / cam.zoom;
      ctx.beginPath();
      for (let x = gx0; x <= x1; x += step) {
        ctx.moveTo(x, y0);
        ctx.lineTo(x, y1);
      }
      for (let y = gy0; y <= y1; y += step) {
        ctx.moveTo(x0, y);
        ctx.lineTo(x1, y);
      }
      ctx.stroke();

      // images
      for (const img of s.images) {
        try {
          const image = new Image();
          image.crossOrigin = "anonymous";
          const url = img.url.startsWith("/api/")
            ? `${window.location.origin}${img.url}`
            : img.url.startsWith("/")
              ? `${window.location.origin}${img.url}`
              : img.url;
          await new Promise<void>((resolve, reject) => {
            image.onload = () => resolve();
            image.onerror = () => reject(new Error("image load failed"));
            image.src = url;
          });
          ctx.drawImage(image, img.x, img.y, img.w, img.h);
        } catch {
          // ignore
        }
      }

      // strokes
      for (const st of s.strokes) {
        if (!st.points.length) continue;
        ctx.strokeStyle = st.color;
        ctx.lineWidth = (st.width / w) / cam.zoom;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        // smooth stroke with quadratic curves through midpoints
        const pts = st.points;
        ctx.beginPath();
        ctx.moveTo(pts[0].x, pts[0].y);
        if (pts.length === 2) {
          ctx.lineTo(pts[1].x, pts[1].y);
        } else {
          for (let i = 1; i < pts.length - 1; i++) {
            const midX = (pts[i].x + pts[i + 1].x) / 2;
            const midY = (pts[i].y + pts[i + 1].y) / 2;
            ctx.quadraticCurveTo(pts[i].x, pts[i].y, midX, midY);
          }
          const last = pts[pts.length - 1];
          ctx.lineTo(last.x, last.y);
        }
        ctx.stroke();
      }

      // texts
      for (const t of s.texts) {
        ctx.fillStyle = t.color;
        ctx.font = `${(t.size / w) / cam.zoom}px Inter, system-ui, sans-serif`;
        ctx.textBaseline = "top";
        ctx.fillText(t.text, t.x, t.y);
      }

      ctx.restore();
    },
    [cam]
  );

  useEffect(() => {
    redraw(state);
  }, [state, redraw]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setStatus("connecting");
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => setStatus("online");
    ws.onclose = () => setStatus("offline");
    ws.onerror = () => setStatus("offline");

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg?.type === "state" && msg.state && typeof msg.state === "object") {
          setState(normalizeState(msg.state));
          historyPastRef.current = [];
          historyFutureRef.current = [];
          syncHistoryFlags();
        } else if (msg?.type === "op" && msg.op) {
          if (msg.op?.op === "cursor") {
            const op = msg.op as {
              op?: string;
              id?: unknown;
              x?: unknown;
              y?: unknown;
              color?: unknown;
              label?: unknown;
            };
            if (
              typeof op.id === "string" &&
              typeof op.x === "number" &&
              typeof op.y === "number" &&
              typeof op.color === "string" &&
              typeof op.label === "string"
            ) {
              const id = op.id;
              if (id !== clientIdRef.current) {
                setCursors((prev) => ({
                  ...prev,
                  [id]: { id, x: op.x, y: op.y, color: op.color, label: op.label, ts: Date.now() } as CursorPresence,
                }));
              }
            }
            return;
          }
          if (msg.op?.op === "cursor_leave") {
            const id = msg.op?.id;
            if (typeof id === "string") {
              setCursors((prev) => {
                const next = { ...prev };
                delete next[id];
                return next;
              });
            }
            return;
          }
          setState((prev) => applyBoardOp(prev, msg.op));
        }
      } catch {
        // ignore
      }
    };

    const clientId = clientIdRef.current;
    return () => {
      try {
        sendOp({ op: "cursor_leave", id: clientId });
        ws.close();
      } catch {
        // ignore
      }
      wsRef.current = null;
    };
  }, [wsUrl, sendOp, syncHistoryFlags]);

  useEffect(() => {
    const t = window.setInterval(() => {
      const now = Date.now();
      setCursors((prev) => {
        const next: Record<string, CursorPresence> = {};
        for (const [id, c] of Object.entries(prev)) {
          if (now - c.ts < 8000) next[id] = c;
        }
        return next;
      });
    }, 2000);
    return () => window.clearInterval(t);
  }, []);

  // Drawing
  const drawingRef = useRef<{ active: boolean; id: string | null }>({ active: false, id: null });
  const panRef = useRef<{ active: boolean; start?: Point; cam0?: Camera }>({ active: false });
  const imageEditRef = useRef<{
    active: boolean;
    id?: string;
    mode?: "move" | "resize";
    corner?: ResizeCorner;
    grab?: Point;
    start?: { x: number; y: number; w: number; h: number };
  }>({ active: false });
  const selectedImage = useMemo(
    () => state.images.find((im) => im.id === selectedImageId) ?? null,
    [state.images, selectedImageId]
  );

  const commitImageUpdate = useCallback(
    (id: string) => {
      const im = stateRef.current.images.find((i) => i.id === id);
      if (!im) return;
      sendOp({ op: "image_update", id, x: im.x, y: im.y, w: im.w, h: im.h });
    },
    [sendOp]
  );

  const updateImageInState = useCallback((id: string, patch: Partial<ImageItem>) => {
    setState((prev) => {
      const cur = normalizeState(prev);
      const images = cur.images.map((im) => (im.id === id ? { ...im, ...patch } : im));
      return { ...cur, images };
    });
  }, []);

  const finishImageEdit = useCallback(() => {
    const edit = imageEditRef.current;
    if (!edit.active) return;
    if (edit.id) commitImageUpdate(edit.id);
    imageEditRef.current = { active: false };
  }, [commitImageUpdate]);

  const eraseAt = useCallback(
    (p: Point) => {
      if (!eraseHistoryPushedRef.current) {
        pushHistory();
        eraseHistoryPushedRef.current = true;
      }
      const r = 0.04 / camRef.current.zoom;
      sendOp({ op: "erase", p, r });
      setState((prev) => applyErase(normalizeState(prev), p, r));
    },
    [sendOp, pushHistory]
  );

  const stopErasing = useCallback(() => {
    erasingRef.current = false;
    eraseHistoryPushedRef.current = false;
  }, []);

  useEffect(() => {
    const endImageEdit = () => finishImageEdit();
    const endErasing = () => stopErasing();
    window.addEventListener("pointerup", endImageEdit);
    window.addEventListener("pointercancel", endImageEdit);
    window.addEventListener("pointerup", endErasing);
    window.addEventListener("pointercancel", endErasing);
    return () => {
      window.removeEventListener("pointerup", endImageEdit);
      window.removeEventListener("pointercancel", endImageEdit);
      window.removeEventListener("pointerup", endErasing);
      window.removeEventListener("pointercancel", endErasing);
    };
  }, [finishImageEdit, stopErasing]);

  const [textDraft, setTextDraft] = useState<{ active: boolean; x: number; y: number; value: string }>({
    active: false,
    x: 0,
    y: 0,
    value: "",
  });

  const onPointerDown = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      if (readonly) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      canvas.setPointerCapture(e.pointerId);

      const pScreen = canvasPoint(canvas, e.clientX, e.clientY);
      const p = screenToWorld(pScreen, cam);
      const hit = findImageAt(normalizeState(state).images, p);

      if (tool === "move" || tool === "image") {
        if (hit) {
          setSelectedImageId(hit.id);
          pushHistory();
          imageEditRef.current = {
            active: true,
            id: hit.id,
            mode: "move",
            grab: { x: p.x - hit.x, y: p.y - hit.y },
          };
          return;
        }
        if (tool === "image") {
          setSelectedImageId(null);
          return;
        }
      } else if (hit && tool !== "erase" && tool !== "pen") {
        setSelectedImageId(hit.id);
      }

      const isPan = e.button === 1 || (e.button === 0 && e.shiftKey) || tool === "move";
      if (isPan) {
        panRef.current = { active: true, start: pScreen, cam0: cam };
        return;
      }
      if (tool === "erase") {
        erasingRef.current = true;
        eraseAt(p);
        return;
      }
      if (tool === "pen") {
        pushHistory();
        const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
        drawingRef.current.active = true;
        drawingRef.current.id = id;
        setState((prev) => ({
          ...normalizeState(prev),
          strokes: [...normalizeState(prev).strokes, { id, color, width, points: [p] }],
        }));
        sendOp({ op: "stroke_begin", id, color, width, p });
      } else if (tool === "text") {
        setTextDraft({ active: true, x: p.x, y: p.y, value: "" });
        window.setTimeout(() => {
          const el = document.getElementById("wb-text-input") as HTMLInputElement | null;
          el?.focus();
        }, 0);
      }
    },
    [readonly, tool, color, width, sendOp, cam, state, pushHistory, eraseAt]
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      if (readonly) return;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const pScreen = canvasPoint(canvas, e.clientX, e.clientY);
      const p = screenToWorld(pScreen, cam);

      // presence (throttled)
      lastCursorRef.current = pScreen;
      if (!cursorSendTimerRef.current) {
        cursorSendTimerRef.current = window.setTimeout(() => {
          cursorSendTimerRef.current = null;
          const cp = lastCursorRef.current;
          if (!cp) return;
          sendOp({
            op: "cursor",
            id: clientIdRef.current,
            x: cp.x,
            y: cp.y,
            color: clientColorRef.current,
            label: clientLabelRef.current,
          });
        }, 60);
      }

      if (panRef.current.active && panRef.current.start && panRef.current.cam0) {
        const dx = pScreen.x - panRef.current.start.x;
        const dy = pScreen.y - panRef.current.start.y;
        setCam({
          ...panRef.current.cam0,
          x: panRef.current.cam0.x - dx / panRef.current.cam0.zoom,
          y: panRef.current.cam0.y - dy / panRef.current.cam0.zoom,
        });
        return;
      }

      if (imageEditRef.current.active && imageEditRef.current.id) {
        const id = imageEditRef.current.id;
        if (imageEditRef.current.mode === "move" && imageEditRef.current.grab) {
          const grab = imageEditRef.current.grab;
          updateImageInState(id, { x: p.x - grab.x, y: p.y - grab.y });
          return;
        }
        if (
          imageEditRef.current.mode === "resize" &&
          imageEditRef.current.corner &&
          imageEditRef.current.start
        ) {
          const rect = computeImageResize(imageEditRef.current.corner, imageEditRef.current.start, p);
          updateImageInState(id, rect);
          return;
        }
      }

      if (tool === "erase" && erasingRef.current) {
        eraseAt(p);
        return;
      }

      if (tool !== "pen") return;
      if (!drawingRef.current.active || !drawingRef.current.id) return;
      const id = drawingRef.current.id;
      setState((prev) => {
        const cur = normalizeState(prev);
        const strokes = cur.strokes.map((s) => (s.id === id ? { ...s, points: [...s.points, p] } : s));
        return { ...cur, strokes };
      });
      scheduleStrokePoint(id, p);
    },
    [readonly, tool, scheduleStrokePoint, sendOp, cam, pushHistory, updateImageInState, eraseAt]
  );

  const onPointerUp = useCallback(
    (e: React.PointerEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (canvas) canvas.releasePointerCapture(e.pointerId);
      drawingRef.current.active = false;
      drawingRef.current.id = null;
      panRef.current.active = false;
      finishImageEdit();
      stopErasing();
    },
    [finishImageEdit, stopErasing]
  );

  const handleImageResizeStart = useCallback(
    (e: React.PointerEvent<HTMLDivElement>, corner: ResizeCorner) => {
      if (readonly || !selectedImageId) return;
      const im = stateRef.current.images.find((i) => i.id === selectedImageId);
      if (!im) return;
      e.stopPropagation();
      e.preventDefault();
      (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
      pushHistory();
      imageEditRef.current = {
        active: true,
        id: im.id,
        mode: "resize",
        corner,
        start: { x: im.x, y: im.y, w: im.w, h: im.h },
      };
    },
    [readonly, selectedImageId, pushHistory]
  );

  const handleOverlayMoveStart = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      if (readonly || !selectedImage) return;
      e.stopPropagation();
      e.preventDefault();
      (e.currentTarget as HTMLDivElement).setPointerCapture(e.pointerId);
      const canvas = canvasRef.current;
      if (!canvas) return;
      const pScreen = canvasPoint(canvas, e.clientX, e.clientY);
      const p = screenToWorld(pScreen, camRef.current);
      pushHistory();
      imageEditRef.current = {
        active: true,
        id: selectedImage.id,
        mode: "move",
        grab: { x: p.x - selectedImage.x, y: p.y - selectedImage.y },
      };
    },
    [readonly, selectedImage, pushHistory]
  );

  const onWrapPointerMove = useCallback(
    (e: React.PointerEvent<HTMLDivElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const pScreen = canvasPoint(canvas, e.clientX, e.clientY);
      const p = screenToWorld(pScreen, camRef.current);

      if (tool === "erase" && erasingRef.current) {
        eraseAt(p);
        return;
      }

      if (!imageEditRef.current.active) return;
      const id = imageEditRef.current.id;
      if (!id) return;
      if (imageEditRef.current.mode === "move" && imageEditRef.current.grab) {
        const grab = imageEditRef.current.grab;
        updateImageInState(id, { x: p.x - grab.x, y: p.y - grab.y });
      } else if (
        imageEditRef.current.mode === "resize" &&
        imageEditRef.current.corner &&
        imageEditRef.current.start
      ) {
        const rect = computeImageResize(imageEditRef.current.corner, imageEditRef.current.start, p);
        updateImageInState(id, rect);
      }
    },
    [updateImageInState, tool, eraseAt]
  );

  const onUploadImage = useCallback(
    async (file: File) => {
      if (uploadInFlightRef.current) return;
      if (!shareToken) {
        alert("Для загрузки картинки нужен share-токен доски.");
        return;
      }
      uploadInFlightRef.current = true;
      try {
        const form = new FormData();
        form.append("file", file);
        const res = await fetch(api.boards.uploadAssetUrl(boardId, shareToken), { method: "POST", body: form });
        if (!res.ok) throw new Error("upload failed");
        const data = await res.json();
        const url = data.url as string;
        const canvas = canvasRef.current;
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const w = clamp(0.4 / cam.zoom, 0.1 / cam.zoom, 0.9 / cam.zoom);
        const h = (w * rect.width) / rect.height;
        const x = cam.x + (0.5 / cam.zoom) - w / 2;
        const y = cam.y + (0.5 / cam.zoom) - h / 2;
        const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;

        pushHistory();
        setState((prev) => {
          const cur = normalizeState(prev);
          const item = { id, x, y, w, h, url };
          return { ...cur, images: [...cur.images, item] };
        });
        sendOp({ op: "image_add", item: { id, x, y, w, h, url } });
        setSelectedImageId(id);
        setTool("image");
      } catch {
        alert("Не удалось загрузить картинку");
      } finally {
        uploadInFlightRef.current = false;
      }
    },
    [boardId, shareToken, sendOp, cam, pushHistory]
  );

  const boardHoverRef = useRef(false);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (!boardHoverRef.current) return;
      e.preventDefault();
      e.stopPropagation();
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      let delta = e.deltaY;
      if (e.deltaMode === 1) delta *= 16;
      if (e.deltaMode === 2) delta *= rect.height;

      setCam((c) => {
        if (e.ctrlKey || e.metaKey) {
          const pScreen = canvasPoint(canvas, e.clientX, e.clientY);
          const before = screenToWorld(pScreen, c);
          const factor = Math.exp(-delta * 0.002);
          const nextZoom = clamp(c.zoom * factor, 0.25, 6);
          const after = screenToWorld(pScreen, { ...c, zoom: nextZoom });
          return {
            ...c,
            zoom: nextZoom,
            x: c.x + (before.x - after.x),
            y: c.y + (before.y - after.y),
          };
        }
        const scale = 1 / c.zoom;
        return {
          ...c,
          x: c.x + ((e.deltaX || 0) / rect.width) * scale,
          y: c.y + (delta / rect.height) * scale,
        };
      });
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  useEffect(() => {
    const blockCtrlZoom = (e: WheelEvent) => {
      if (!boardHoverRef.current) return;
      if (e.ctrlKey || e.metaKey) e.preventDefault();
    };
    document.addEventListener("wheel", blockCtrlZoom, { passive: false, capture: true });
    return () => document.removeEventListener("wheel", blockCtrlZoom, { capture: true });
  }, []);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target) {
        const tag = target.tagName?.toLowerCase();
        if (tag === "input" || tag === "textarea" || target.isContentEditable) return;
      }
      const key = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && key === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
        return;
      }
      if ((e.ctrlKey || e.metaKey) && (key === "y" || (key === "z" && e.shiftKey))) {
        e.preventDefault();
        redo();
        return;
      }
      if (readonly) return;
      if (key === "p") {
        e.preventDefault();
        setTool("pen");
      } else if (key === "e") {
        e.preventDefault();
        setTool("erase");
      } else if (key === "m") {
        e.preventDefault();
        setTool("move");
      } else if (key === "escape") {
        setSelectedImageId(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [readonly, undo, redo]);

  // Global paste support (Ctrl+V) without switching tools.
  useEffect(() => {
    const onPaste = (e: ClipboardEvent) => {
      // Ignore if typing into an input/textarea/contenteditable
      const target = e.target as HTMLElement | null;
      if (target) {
        const tag = target.tagName?.toLowerCase();
        if (tag === "input" || tag === "textarea" || target.isContentEditable) return;
      }
      const item = e.clipboardData?.items?.[0];
      if (!item) return;
      if (item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) {
          e.preventDefault();
          onUploadImage(file).catch(() => {});
        }
      }
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [onUploadImage]);

  return (
    <div className={fullscreen ? "w-full h-full" : "space-y-3"}>
      <div
        ref={wrapRef}
        className={
          fullscreen
            ? "w-full h-full bg-white overflow-hidden relative pt-14"
            : "rounded-2xl border bg-white overflow-hidden relative pt-14"
        }
        tabIndex={0}
        onMouseEnter={() => {
          boardHoverRef.current = true;
        }}
        onMouseLeave={() => {
          boardHoverRef.current = false;
        }}
        onPointerMove={onWrapPointerMove}
        onDragOver={(e) => {
          e.preventDefault();
        }}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f && f.type.startsWith("image/")) onUploadImage(f).catch(() => alert("Не удалось загрузить картинку"));
        }}
      >
        {textDraft.active && (
          <input
            id="wb-text-input"
            value={textDraft.value}
            onChange={(e) => setTextDraft((p) => ({ ...p, value: e.target.value }))}
            onKeyDown={(e) => {
              if (e.key === "Escape") setTextDraft({ active: false, x: 0, y: 0, value: "" });
              if (e.key === "Enter") {
                const v = textDraft.value.trim();
                if (v) {
                  pushHistory();
                  const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
                  const item = { id, x: textDraft.x, y: textDraft.y, text: v, color, size: textSize };
                  setState((prev) => ({ ...normalizeState(prev), texts: [...normalizeState(prev).texts, item] }));
                  sendOp({ op: "text_add", item });
                }
                setTextDraft({ active: false, x: 0, y: 0, value: "" });
              }
            }}
            onBlur={() => setTextDraft({ active: false, x: 0, y: 0, value: "" })}
            className="absolute z-10 px-2 py-1 rounded-md border bg-white shadow-sm"
            style={{
              left: `${worldToScreen({ x: textDraft.x, y: textDraft.y }, cam).x * 100}%`,
              top: `${worldToScreen({ x: textDraft.x, y: textDraft.y }, cam).y * 100}%`,
              transform: "translate(0, 0)",
              width: "min(70%, 520px)",
            }}
            placeholder="Введите текст…"
          />
        )}
        <canvas
          ref={canvasRef}
          className={fullscreen ? "w-full h-full touch-none" : "w-full h-[70vh] touch-none"}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerCancel={onPointerUp}
          onPointerLeave={() => sendOp({ op: "cursor_leave", id: clientIdRef.current })}
        />
        {selectedImage && !readonly && (
          <div className="absolute z-[15] pointer-events-none" style={imageScreenStyle(selectedImage, cam)}>
            <div className="absolute inset-0 border-2 border-blue-500 rounded-sm" />
            {(tool === "image" || tool === "move") && (
              <div
                className="absolute inset-0 cursor-move pointer-events-auto"
                onPointerDown={handleOverlayMoveStart}
                onPointerUp={() => finishImageEdit()}
                onPointerCancel={() => finishImageEdit()}
              />
            )}
            {(["nw", "ne", "sw", "se"] as ResizeCorner[]).map((corner) => (
              <div
                key={corner}
                className="absolute w-3.5 h-3.5 bg-white border-2 border-blue-500 rounded-sm pointer-events-auto z-20 shadow"
                style={{
                  left: corner.includes("w") ? -7 : undefined,
                  right: corner.includes("e") ? -7 : undefined,
                  top: corner.includes("n") ? -7 : undefined,
                  bottom: corner.includes("s") ? -7 : undefined,
                  cursor: corner === "nw" || corner === "se" ? "nwse-resize" : "nesw-resize",
                }}
                onPointerDown={(e) => handleImageResizeStart(e, corner)}
                onPointerUp={() => finishImageEdit()}
                onPointerCancel={() => finishImageEdit()}
              />
            ))}
          </div>
        )}
        <div className="absolute inset-0 pointer-events-none">
          {Object.values(cursors).map((c) => (
            <div
              key={c.id}
              className="absolute"
              style={{
                left: `${c.x * 100}%`,
                top: `${c.y * 100}%`,
                transform: "translate(6px, 6px)",
              }}
            >
              <div className="flex items-center gap-2">
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 9999,
                    background: c.color,
                    boxShadow: "0 0 0 2px rgba(255,255,255,0.9)",
                  }}
                />
                <div
                  className="text-[11px] px-2 py-0.5 rounded-full"
                  style={{
                    background: "rgba(15, 23, 42, 0.85)",
                    color: "white",
                  }}
                >
                  {c.label}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Top horizontal toolbar */}
        <div className="absolute top-3 left-3 right-3 z-20 pointer-events-auto flex justify-center">
          <div className="flex flex-wrap items-center gap-1.5 px-2 py-2 bg-white/95 backdrop-blur border border-slate-200 shadow-lg rounded-2xl max-w-full">
            <div
              className={`w-2.5 h-2.5 rounded-full shrink-0 ${status === "online" ? "bg-emerald-500" : status === "connecting" ? "bg-amber-400" : "bg-slate-300"}`}
              title={status === "online" ? "Онлайн" : status === "connecting" ? "Подключение…" : "Оффлайн"}
            />
            <div className="w-px h-7 bg-slate-200 shrink-0" />
            <button
              className={`p-2 rounded-xl border ${tool === "move" ? "bg-slate-900 text-white border-slate-900" : "bg-white hover:bg-slate-50"}`}
              onClick={() => setTool("move")}
              disabled={readonly}
              title="Перемещение (M, Shift+ЛКМ)"
            >
              <CursorArrowRaysIcon className="w-5 h-5" />
            </button>
            <button
              className={`p-2 rounded-xl border ${tool === "pen" ? "bg-slate-900 text-white border-slate-900" : "bg-white hover:bg-slate-50"}`}
              onClick={() => setTool("pen")}
              disabled={readonly}
              title="Ручка (P)"
            >
              <PencilIcon className="w-5 h-5" />
            </button>
            <button
              className={`p-2 rounded-xl border ${tool === "erase" ? "bg-slate-900 text-white border-slate-900" : "bg-white hover:bg-slate-50"}`}
              onClick={() => setTool("erase")}
              disabled={readonly}
              title="Ластик (E) — штрихи, текст, картинки"
            >
              <TrashIcon className="w-5 h-5" />
            </button>
            <button
              className={`p-2 rounded-xl border ${tool === "text" ? "bg-slate-900 text-white border-slate-900" : "bg-white hover:bg-slate-50"}`}
              onClick={() => setTool("text")}
              disabled={readonly}
              title="Текст"
            >
              <span className="w-5 h-5 flex items-center justify-center text-base font-bold">T</span>
            </button>
            <button
              className={`p-2 rounded-xl border ${tool === "image" ? "bg-slate-900 text-white border-slate-900" : "bg-white hover:bg-slate-50"}`}
              onClick={() => setTool("image")}
              disabled={readonly}
              title="Картинки: перетащить, углы — размер"
            >
              <PhotoIcon className="w-5 h-5" />
            </button>
            <div className="w-px h-7 bg-slate-200 shrink-0 hidden sm:block" />
            <input
              type="color"
              value={color}
              onChange={(e) => setColor(e.target.value)}
              className="w-9 h-9 p-0.5 border rounded-lg shrink-0 hidden sm:block"
              disabled={readonly}
              title="Цвет"
            />
            <input
              type="range"
              min={1}
              max={14}
              value={width}
              onChange={(e) => setWidth(Number(e.target.value))}
              disabled={readonly}
              className="w-16 sm:w-20 shrink-0 hidden sm:block"
              title="Толщина линии"
            />
            <input
              type="range"
              min={12}
              max={72}
              value={textSize}
              onChange={(e) => setTextSize(Number(e.target.value))}
              disabled={readonly}
              className="w-16 sm:w-20 shrink-0 hidden md:block"
              title="Размер текста"
            />
            <div className="w-px h-7 bg-slate-200 shrink-0" />
            <button
              className="p-2 rounded-xl border bg-white hover:bg-slate-50 disabled:opacity-40"
              onClick={undo}
              disabled={!canUndo}
              title="Отменить (Ctrl+Z)"
            >
              <ArrowUturnLeftIcon className="w-5 h-5" />
            </button>
            <button
              className="p-2 rounded-xl border bg-white hover:bg-slate-50 disabled:opacity-40"
              onClick={redo}
              disabled={!canRedo}
              title="Повторить (Ctrl+Y)"
            >
              <ArrowUturnRightIcon className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-0.5 shrink-0">
              <button
                className="p-1.5 rounded-lg border hover:bg-slate-50"
                onClick={() => setCam((c) => ({ ...c, zoom: clamp(c.zoom / 1.1, 0.25, 6) }))}
                title="Отдалить"
              >
                <MinusIcon className="w-4 h-4" />
              </button>
              <span className="text-xs w-10 text-center tabular-nums">{Math.round(cam.zoom * 100)}%</span>
              <button
                className="p-1.5 rounded-lg border hover:bg-slate-50"
                onClick={() => setCam((c) => ({ ...c, zoom: clamp(c.zoom * 1.1, 0.25, 6) }))}
                title="Приблизить"
              >
                <PlusIcon className="w-4 h-4" />
              </button>
            </div>
            {!readonly && (
              <>
                <label
                  className="p-2 rounded-xl border bg-white cursor-pointer hover:bg-slate-50 shrink-0"
                  title="Загрузить картинку"
                >
                  <ArrowDownTrayIcon className="w-5 h-5" />
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) onUploadImage(f).catch(() => alert("Не удалось загрузить картинку"));
                      e.currentTarget.value = "";
                    }}
                  />
                </label>
                <button
                  className="px-2.5 py-2 rounded-xl border bg-white text-xs hover:bg-red-50 hover:text-red-600 shrink-0"
                  onClick={() => {
                    if (!confirm("Очистить доску?")) return;
                    pushHistory();
                    setState({ ...DEFAULT_STATE });
                    sendOp({ op: "clear" });
                  }}
                  title="Очистить всю доску"
                >
                  Очистить
                </button>
              </>
            )}
            <p className="hidden lg:block text-[10px] text-slate-500 leading-tight max-w-[220px] ml-1">
              P/E/M · колесо — пан · Ctrl+колесо — зум доски · картинка: углы — размер
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

