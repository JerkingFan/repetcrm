"""Whiteboard state: geometry, stroke simplification, op application."""

from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any

from app.models import Board

WRITE_OPS = frozenset(
    {
        "set_state",
        "clear",
        "stroke_begin",
        "stroke_point",
        "stroke_simplify",
        "text_add",
        "image_add",
        "image_move",
        "image_update",
        "erase",
    }
)


def is_persisted_write_op(op: dict) -> bool:
    return op.get("op") in WRITE_OPS


def board_to_dict(b: Board) -> dict:
    try:
        state = json.loads(b.state_json or "{}")
        if not isinstance(state, dict):
            state = {}
    except Exception:
        state = {}
    state = {
        "version": 1,
        "strokes": state.get("strokes") if isinstance(state.get("strokes"), list) else [],
        "texts": state.get("texts") if isinstance(state.get("texts"), list) else [],
        "images": state.get("images") if isinstance(state.get("images"), list) else [],
    }
    return {
        "id": b.id,
        "owner_id": b.owner_id,
        "title": b.title,
        "share_token": b.share_token,
        "share_writable": bool(b.share_writable),
        "state_json": state,
        "created_at": b.created_at.isoformat() if isinstance(b.created_at, datetime) else str(b.created_at),
        "updated_at": b.updated_at.isoformat() if isinstance(b.updated_at, datetime) else str(b.updated_at),
    }


def load_state(b: Board) -> dict:
    try:
        state = json.loads(b.state_json or "{}")
        if not isinstance(state, dict):
            state = {}
    except Exception:
        state = {}
    return {
        "version": 1,
        "strokes": state.get("strokes") if isinstance(state.get("strokes"), list) else [],
        "texts": state.get("texts") if isinstance(state.get("texts"), list) else [],
        "images": state.get("images") if isinstance(state.get("images"), list) else [],
    }


def _perpendicular_distance(p: dict, a: dict, b: dict) -> float:
    ax, ay = float(a["x"]), float(a["y"])
    bx, by = float(b["x"]), float(b["y"])
    px, py = float(p["x"]), float(p["y"])
    dx = bx - ax
    dy = by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    proj_x = ax + t * dx
    proj_y = ay + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def _douglas_peucker(points: list[dict], epsilon: float) -> list[dict]:
    if len(points) <= 2:
        return points
    max_dist = 0.0
    index = 0
    end = len(points) - 1
    for i in range(1, end):
        d = _perpendicular_distance(points[i], points[0], points[end])
        if d > max_dist:
            max_dist = d
            index = i
    if max_dist > epsilon:
        left = _douglas_peucker(points[: index + 1], epsilon)
        right = _douglas_peucker(points[index:], epsilon)
        return left[:-1] + right
    return [points[0], points[end]]


def simplify_stroke_points(points: list, epsilon: float = 0.002) -> list:
    clean = []
    for pt in points:
        if not isinstance(pt, dict):
            continue
        x, y = pt.get("x"), pt.get("y")
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            clean.append({"x": float(x), "y": float(y)})
    if len(clean) <= 3:
        return clean
    return _douglas_peucker(clean, epsilon)


def compact_state(state: dict) -> None:
    """Упрощает полилинии in-place перед записью в БД."""
    for st in state.get("strokes", []):
        if not isinstance(st, dict):
            continue
        pts = st.get("points")
        if isinstance(pts, list) and len(pts) > 4:
            st["points"] = simplify_stroke_points(pts)


def _text_hit(t: dict, px: float, py: float, r: float) -> bool:
    if not isinstance(t, dict):
        return False
    x = t.get("x")
    y = t.get("y")
    text = t.get("text")
    size = t.get("size")
    if not all(isinstance(v, (int, float)) for v in (x, y, size)) or not isinstance(text, str):
        return False
    w = max(len(text), 1) * float(size) * 0.55
    h = float(size) * 1.25
    return (
        float(px) >= float(x) - r
        and float(px) <= float(x) + w + r
        and float(py) >= float(y) - r
        and float(py) <= float(y) + h + r
    )


def _image_hit(im: dict, px: float, py: float, r: float) -> bool:
    if not isinstance(im, dict):
        return False
    x = im.get("x")
    y = im.get("y")
    w = im.get("w")
    h = im.get("h")
    if not all(isinstance(v, (int, float)) for v in (x, y, w, h)):
        return False
    return (
        float(px) >= float(x) - r
        and float(px) <= float(x) + float(w) + r
        and float(py) >= float(y) - r
        and float(py) <= float(y) + float(h) + r
    )


def apply_op(state: dict, op: dict) -> dict:
    t = op.get("op")
    if t in ("cursor", "cursor_leave"):
        return state
    if t == "set_state":
        new_state = op.get("state")
        if not isinstance(new_state, dict):
            return state
        return {
            "version": 1,
            "strokes": new_state.get("strokes") if isinstance(new_state.get("strokes"), list) else [],
            "texts": new_state.get("texts") if isinstance(new_state.get("texts"), list) else [],
            "images": new_state.get("images") if isinstance(new_state.get("images"), list) else [],
        }
    if t == "clear":
        return {"version": 1, "strokes": [], "texts": [], "images": []}

    if t == "stroke_begin":
        sid = op.get("id")
        if not isinstance(sid, str) or not sid:
            return state
        color = op.get("color") if isinstance(op.get("color"), str) else "#1E3A8A"
        width = op.get("width") if isinstance(op.get("width"), (int, float)) else 3
        p = op.get("p")
        if not isinstance(p, dict) or "x" not in p or "y" not in p:
            return state
        state["strokes"].append({"id": sid, "color": color, "width": width, "points": [p]})
        return state

    if t == "stroke_point":
        sid = op.get("id")
        p = op.get("p")
        if not isinstance(sid, str) or not isinstance(p, dict):
            return state
        for st in reversed(state["strokes"]):
            if st.get("id") == sid and isinstance(st.get("points"), list):
                st["points"].append(p)
                break
        return state

    if t == "stroke_simplify":
        sid = op.get("id")
        points = op.get("points")
        if not isinstance(sid, str) or not isinstance(points, list):
            return state
        simplified = simplify_stroke_points(points, epsilon=0.002)
        for st in state.get("strokes", []):
            if isinstance(st, dict) and st.get("id") == sid:
                st["points"] = simplified if len(simplified) >= 2 else st.get("points", [])
                break
        return state

    if t == "text_add":
        item = op.get("item")
        if isinstance(item, dict):
            state["texts"].append(item)
        return state

    if t == "image_add":
        item = op.get("item")
        if isinstance(item, dict):
            iid = item.get("id")
            if isinstance(iid, str) and iid:
                for it in state.get("images", []):
                    if isinstance(it, dict) and it.get("id") == iid:
                        return state
            state["images"].append(item)
        return state

    if t == "image_move":
        iid = op.get("id")
        x = op.get("x")
        y = op.get("y")
        if not isinstance(iid, str) or not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return state
        for it in state.get("images", []):
            if isinstance(it, dict) and it.get("id") == iid:
                it["x"] = x
                it["y"] = y
                break
        return state

    if t == "image_update":
        iid = op.get("id")
        x = op.get("x")
        y = op.get("y")
        w = op.get("w")
        h = op.get("h")
        if (
            not isinstance(iid, str)
            or not isinstance(x, (int, float))
            or not isinstance(y, (int, float))
            or not isinstance(w, (int, float))
            or not isinstance(h, (int, float))
        ):
            return state
        for it in state.get("images", []):
            if isinstance(it, dict) and it.get("id") == iid:
                it["x"] = float(x)
                it["y"] = float(y)
                it["w"] = max(0.02, float(w))
                it["h"] = max(0.02, float(h))
                break
        return state

    if t == "erase":
        p = op.get("p")
        r = op.get("r")
        if not isinstance(p, dict) or not isinstance(r, (int, float)):
            return state
        px = p.get("x")
        py = p.get("y")
        if not isinstance(px, (int, float)) or not isinstance(py, (int, float)):
            return state
        r2 = float(r) * float(r)
        strokes = []
        for st in state.get("strokes", []):
            if not isinstance(st, dict):
                continue
            pts = st.get("points")
            if not isinstance(pts, list):
                continue
            hit = False
            for pt in pts:
                if not isinstance(pt, dict):
                    continue
                x = pt.get("x")
                y = pt.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    dx = float(x) - float(px)
                    dy = float(y) - float(py)
                    if dx * dx + dy * dy <= r2:
                        hit = True
                        break
            if not hit:
                strokes.append(st)
        state["strokes"] = strokes
        texts = []
        for titem in state.get("texts", []):
            if not _text_hit(titem, float(px), float(py), float(r)):
                texts.append(titem)
        state["texts"] = texts
        images = []
        for im in state.get("images", []):
            if not _image_hit(im, float(px), float(py), float(r)):
                images.append(im)
        state["images"] = images
        return state

    return state
