"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   AMRITA EMERGENCY GPS — Python DSA Backend  v4.1                          ║
║   Ettimadai Campus · 22 Real Nodes · Real Hostel Names                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  GET  /api/graph              → Full campus graph                           ║
║  GET  /api/nodes              → All 22 nodes with metadata                 ║
║  POST /api/pathfind           → Dijkstra / A* + GPS directions + ETA       ║
║  POST /api/dispatch           → Emergency tile: fire / medical / security  ║
║  POST /api/resource           → Nearest resource (Hash Map O(1) lookup)    ║
║  POST /api/roadblock/add      → Block a road                               ║
║  POST /api/roadblock/remove   → Unblock a road                             ║
║  GET  /api/roadblock/list     → All currently blocked roads                ║
║  POST /api/roadblock/clear    → Remove all blocks                          ║
║  GET  /api/complexity         → Full DSA complexity reference              ║
╚══════════════════════════════════════════════════════════════════════════════╝

Install:  pip install flask flask-cors
Run:      python backend_v4.py
"""

import heapq, math, time
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT 1 — NODE HASH MAP  (22 real campus buildings)
# O(1) lookup by node ID
# ═══════════════════════════════════════════════════════════════════════════════

nodes = {
    # Entrance & Admin
    "GATE":   {"name": "Main Entrance Gate",          "short": "Main Gate",   "sector": "entrance",  "x": 80,  "y": 430},
    "ADMIN":  {"name": "Admin Block",                 "short": "Admin",       "sector": "entrance",  "x": 160, "y": 430},
    "GUEST":  {"name": "Guest House",                 "short": "Guest House", "sector": "entry",     "x": 170, "y": 355},
    # Central Hub
    "CANT_M": {"name": "Main Canteen",                "short": "Main Canteen","sector": "central",   "x": 295, "y": 400},
    "CANT_MBA":{"name":"MBA Canteen",                 "short": "MBA Canteen", "sector": "south",     "x": 455, "y": 450},
    "MBA":    {"name": "ASB (MBA Block)",              "short": "MBA Block",   "sector": "south",     "x": 535, "y": 475},
    # Academic
    "LIB":    {"name": "Central Library",             "short": "Library",     "sector": "academic",  "x": 215, "y": 240},
    "AB1":    {"name": "Academic Block 1",            "short": "AB1",         "sector": "academic",  "x": 415, "y": 278},
    "AB2":    {"name": "Academic Block 2",            "short": "AB2",         "sector": "academic",  "x": 555, "y": 308},
    "AB3":    {"name": "Academic Block 3",            "short": "AB3",         "sector": "academic",  "x": 700, "y": 262},
    # Research
    "TIFAC":  {"name": "TIFAC Core Labs",             "short": "TIFAC",       "sector": "research",  "x": 525, "y": 183},
    # Medical
    "CLIN":   {"name": "Health Centre",               "short": "Clinic",      "sector": "medical",   "x": 172, "y": 158},
    # Girls Hostels (Real Bhavanam names)
    "MYTH":   {"name": "Mythreyi Bhavanam",           "short": "Mythreyi",    "sector": "hostel_g",  "x": 325, "y": 103},
    "GARGI":  {"name": "Gargi Bhavanam",              "short": "Gargi",       "sector": "hostel_g",  "x": 445, "y": 78},
    "ADITHI": {"name": "Adithi Bhavanam",             "short": "Adithi",      "sector": "hostel_g",  "x": 245, "y": 80},
    # Boys Hostels (Real Bhavanam names)
    "VASISH": {"name": "Vasishta Bhavanam",           "short": "Vasishta",    "sector": "hostel_b",  "x": 752, "y": 163},
    "AGAS":   {"name": "Agasthya Bhavanam",           "short": "Agasthya",    "sector": "hostel_b",  "x": 822, "y": 198},
    "NACH":   {"name": "Nachiketas Bhavanam",         "short": "Nachiketas",  "sector": "hostel_b",  "x": 840, "y": 280},
    "VYASA":  {"name": "Sri Vyasa Maharishi Bhavanam","short": "Vyasa",       "sector": "hostel_b",  "x": 755, "y": 300},
    # Sports
    "POOL":   {"name": "Olympic Swimming Pool",       "short": "Pool",        "sector": "sports",    "x": 642, "y": 118},
    "GROUND": {"name": "Sports Ground & Track",       "short": "Sports Gnd",  "sector": "sports",    "x": 740, "y": 390},
    # Spiritual
    "TEMPLE": {"name": "Amrita Nagar Temple",         "short": "Temple",      "sector": "spiritual", "x": 100, "y": 310},
}

# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT 1 — EDGE LIST (Adjacency List)
# ═══════════════════════════════════════════════════════════════════════════════

BASE_EDGES = [
    # Entrance & Admin
    ("GATE",     "ADMIN",    80,   "Admin Entry Road"),
    ("GATE",     "TEMPLE",   130,  "Temple Path"),
    ("GATE",     "LIB",      550,  "Perimeter West Road"),
    ("ADMIN",    "GUEST",    100,  "Admin-Guest Road"),
    ("ADMIN",    "CANT_M",   200,  "Admin-Canteen Road"),
    ("GUEST",    "CANT_M",   280,  "Connector Road"),
    ("GUEST",    "LIB",      210,  "Guest-Library Path"),
    # Academic core
    ("CANT_M",   "AB1",      280,  "Main Academic Walk"),
    ("CANT_M",   "CANT_MBA", 350,  "South Loop"),
    ("CANT_MBA", "MBA",       80,  "Service Path"),
    ("LIB",      "AB1",      240,  "Library Connector"),
    ("LIB",      "CLIN",     100,  "Academic-Medical Link"),
    ("LIB",      "ADITHI",   160,  "North Campus Road"),
    ("AB1",      "AB2",      160,  "Block Inter-connect"),
    ("AB2",      "AB3",      210,  "Main Corridor"),
    ("AB3",      "TIFAC",    110,  "Lab Access Path"),
    ("AB3",      "VASISH",   220,  "North-East Road"),
    ("AB3",      "GROUND",   180,  "Sports Access Road"),
    ("TIFAC",    "AB2",      170,  "Research Connector"),
    ("TIFAC",    "AB1",      320,  "Central Spine Road"),
    ("TIFAC",    "POOL",     250,  "Sports Perimeter Road"),
    # Girls Hostels
    ("CLIN",     "MYTH",     120,  "Medical Emergency Lane"),
    ("MYTH",     "GARGI",     90,  "Girls Hostel Interior Path"),
    ("MYTH",     "ADITHI",   100,  "Girls Hostel Cross Road"),
    # Boys Hostels
    ("VASISH",   "AGAS",     110,  "Boys Hostel Loop"),
    ("AGAS",     "NACH",      90,  "Nachiketas Access Road"),
    ("NACH",     "VYASA",     85,  "Vyasa Link Road"),
    ("VYASA",    "GROUND",   120,  "Sports-Hostel Path"),
    # Sports
    ("POOL",     "VASISH",   130,  "Sports-Hostel Path"),
    ("GROUND",   "AB3",      180,  "Sports Access Road"),
]

# ─── Resource Hash Map — O(1) key lookup ─────────────────────────────────────
RESOURCE_MAP = {
    "fire_ext":      ["GATE","LIB","AB1","AB2","AB3","CLIN","TIFAC","CANT_M","VASISH","MYTH","ADMIN"],
    "med_kit":       ["GATE","CANT_M","LIB","AB1","AB3","CLIN","MBA","TIFAC","MYTH","ADMIN"],
    "water_src":     ["POOL","GATE","LIB","GROUND"],
    "defibrillator": ["CLIN","POOL"],
}

AVG_SPEED_MPS = 1.8   # walking pace for ETA
blocked_edges: set = set()


# ═══════════════════════════════════════════════════════════════════════════════
# GRAPH BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_graph():
    g = {n: {} for n in nodes}
    meta = {}
    for src, dst, dist, road in BASE_EDGES:
        k1, k2 = f"{src}-{dst}", f"{dst}-{src}"
        if k1 not in blocked_edges and k2 not in blocked_edges:
            g[src][dst] = dist
            g[dst][src] = dist
        meta[k1] = meta[k2] = road
    return g, meta


# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT 2 — MIN-HEAP
# insert O(log n) · extract_min O(log n)
# ═══════════════════════════════════════════════════════════════════════════════

class MinHeap:
    def __init__(self):
        self._h = []
        self._c = 0

    def insert(self, node, priority):
        heapq.heappush(self._h, (priority, self._c, node))
        self._c += 1

    def extract_min(self):
        if self._h:
            p, _, n = heapq.heappop(self._h)
            return n, p
        return None, None

    def is_empty(self):
        return not self._h


# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT 3A — DIJKSTRA   O(E log V)
# ═══════════════════════════════════════════════════════════════════════════════

def dijkstra(source, target, graph=None):
    """
    Exhaustive shortest path.
    Key step: edge relaxation — if dist[u]+w < dist[v], update dist[v].
    Used for: Fire suppression, Security lockdown, hub destinations.
    """
    if graph is None:
        graph, _ = build_graph()

    dist   = {n: math.inf for n in nodes}
    parent = {n: None for n in nodes}
    vis, steps = set(), []

    dist[source] = 0
    pq = MinHeap()
    pq.insert(source, 0)

    while not pq.is_empty():
        u, d = pq.extract_min()
        if u in vis: continue
        vis.add(u); steps.append({"node": u, "g": d, "h": 0})
        if u == target: break
        for v, w in graph[u].items():
            if v not in vis:
                nd = dist[u] + w
                if nd < dist[v]:
                    dist[v] = nd; parent[v] = u; pq.insert(v, nd)

    path = _backtrack(parent, source, target)
    return path, dist[target], steps


# ═══════════════════════════════════════════════════════════════════════════════
# SPRINT 3B — A* SEARCH   O(E log V) guided
# ═══════════════════════════════════════════════════════════════════════════════

def heuristic(a, b):
    """Euclidean distance × 1.5 scale factor. Admissible → A* is optimal."""
    ax, ay = nodes[a]["x"], nodes[a]["y"]
    bx, by = nodes[b]["x"], nodes[b]["y"]
    return math.sqrt((bx-ax)**2 + (by-ay)**2) * 1.5

def astar(source, target, graph=None):
    """
    f(n) = g(n) + h(n)
    g = known cost from source
    h = Euclidean heuristic (guides search toward target)
    Used for: Ambulance dispatch, student navigation.
    """
    if graph is None:
        graph, _ = build_graph()

    g_sc = {n: math.inf for n in nodes}
    parent = {n: None for n in nodes}
    vis, steps = set(), []

    g_sc[source] = 0
    pq = MinHeap()
    pq.insert(source, heuristic(source, target))

    while not pq.is_empty():
        u, _ = pq.extract_min()
        if u in vis: continue
        vis.add(u)
        h_val = round(heuristic(u, target), 2)
        steps.append({"node": u, "g": g_sc[u], "h": h_val})
        if u == target: break
        for v, w in graph[u].items():
            if v not in vis:
                tg = g_sc[u] + w
                if tg < g_sc[v]:
                    g_sc[v] = tg; parent[v] = u
                    pq.insert(v, tg + heuristic(v, target))

    path = _backtrack(parent, source, target)
    return path, g_sc[target], steps

def _backtrack(parent, src, tgt):
    p, c = [], tgt
    while c is not None: p.append(c); c = parent[c]
    p.reverse()
    return p if p and p[0] == src else None


# ═══════════════════════════════════════════════════════════════════════════════
# GPS DIRECTIONS GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def _bearing(ax, ay, bx, by):
    return math.degrees(math.atan2(by - ay, bx - ax))

def generate_gps_directions(path, graph, edge_meta):
    """
    Compute turn-by-turn instructions from road segment bearing angles.
    |Δangle| < 25°  → straight  |  25–155° → left  |  -155 to -25° → right
    """
    out = []
    for i, nid in enumerate(path):
        prev, nxt = (path[i-1] if i > 0 else None), (path[i+1] if i < len(path)-1 else None)
        n = nodes[nid]
        road = edge_meta.get(f"{nid}-{nxt}", "Campus Road") if nxt else None
        dist_ahead = graph[nid].get(nxt, 0) if nxt else 0

        if not prev:        icon, txt = "📍", "Start at"
        elif not nxt:       icon, txt = "🏁", "Arrive at"
        else:
            p, c, nx = nodes[prev], nodes[nid], nodes[nxt]
            d1 = _bearing(p["x"], p["y"], c["x"], c["y"])
            d2 = _bearing(c["x"], c["y"], nx["x"], nx["y"])
            delta = d2 - d1
            while delta > 180:  delta -= 360
            while delta < -180: delta += 360
            if   abs(delta) < 25:           icon, txt = "⬆", "Continue straight to"
            elif 25 <= delta < 155:         icon, txt = "↙", "Turn left towards"
            elif -155 < delta <= -25:       icon, txt = "↘", "Turn right towards"
            else:                           icon, txt = "↩", "U-turn towards"

        out.append({
            "step": i+1, "node_id": nid, "node_name": n["name"],
            "node_short": n["short"], "sector": n["sector"],
            "icon": icon, "direction": txt,
            "road_ahead": road, "dist_ahead": dist_ahead,
            "is_last": nxt is None,
            "coords": {"x": n["x"], "y": n["y"]},
        })
    return out

def calculate_eta(dist):
    s = dist / AVG_SPEED_MPS
    return {"seconds": round(s), "formatted": f"{int(s//60)}m {int(s%60):02d}s", "speed_mps": AVG_SPEED_MPS}

def find_nearest_resource(source, rtype):
    cands = RESOURCE_MAP.get(rtype, [])   # O(1) hash lookup
    graph, meta = build_graph()
    best_n, best_p, best_d = None, None, math.inf
    for t in cands:
        if t == source: continue
        p, d, _ = dijkstra(source, t, graph)
        if p and d < best_d: best_d = d; best_p = p; best_n = t
    return best_n, best_p, best_d, graph, meta


# ═══════════════════════════════════════════════════════════════════════════════
# SHARED RESPONSE BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

def build_response(algo, path, dist, steps, graph, meta, dtype="manual"):
    segs = [{"from": path[i], "to": path[i+1],
             "dist": graph[path[i]][path[i+1]],
             "road": meta.get(f"{path[i]}-{path[i+1]}", "Campus Road")}
            for i in range(len(path)-1)]
    return {
        "algorithm": algo, "dispatch_type": dtype,
        "path": path, "total_dist": dist, "segments": segs,
        "gps_directions": generate_gps_directions(path, graph, meta),
        "eta": calculate_eta(dist),
        "nodes_explored": len(steps),
        "radar_scan_order": [s["node"] for s in steps],
        "radar_scan_detail": steps,
        "blocked_roads": len(blocked_edges),
        "source": path[0], "destination": path[-1],
        "source_name": nodes[path[0]]["name"],
        "dest_name": nodes[path[-1]]["name"],
        "complexity": {
            "time": "O(E log V)", "space": "O(V + E)",
            "structure": "Min-Heap PQ" if algo == "dijkstra" else "Min-Heap + Euclidean h(n)",
            "heuristic": "None (exhaustive)" if algo == "dijkstra" else "h(n)=√((x₂-x₁)²+(y₂-y₁)²)×1.5",
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/graph")
def get_graph():
    g, _ = build_graph()
    return jsonify({
        "nodes": nodes,
        "edges": [{"src": s, "dst": d, "dist": w, "road": r,
                   "blocked": f"{s}-{d}" in blocked_edges or f"{d}-{s}" in blocked_edges}
                  for s, d, w, r in BASE_EDGES],
        "resource_map": RESOURCE_MAP,
        "total_nodes": len(nodes),
        "total_edges": len(BASE_EDGES),
        "blocked_count": len(blocked_edges),
    })

@app.route("/api/nodes")
def get_nodes():
    return jsonify(nodes)

@app.route("/api/pathfind", methods=["POST"])
def pathfind():
    """
    Manual navigation — auto-selects algorithm:
    Dijkstra for hub/gate destinations, A* for specific targets.
    """
    data = request.get_json()
    src  = data.get("source", "").upper()
    tgt  = data.get("target", "").upper()
    # Honour explicit override if provided, else auto-select
    algo = data.get("algorithm", "auto").lower()

    if src not in nodes: return jsonify({"error": f"Invalid source: {src}"}), 400
    if tgt not in nodes: return jsonify({"error": f"Invalid target: {tgt}"}), 400
    if src == tgt:       return jsonify({"error": "Source = destination"}), 400

    hub_nodes = {"GATE","ADMIN","CANT_M","LIB"}
    if algo == "auto":
        algo = "dijkstra" if tgt in hub_nodes else "astar"

    graph, meta = build_graph()
    t0 = time.perf_counter()
    path, dist, steps = (astar if algo=="astar" else dijkstra)(src, tgt, graph)
    ms = round((time.perf_counter()-t0)*1000, 3)

    if not path: return jsonify({"error": "No path — may be blocked"}), 404

    r = build_response(algo, path, dist, steps, graph, meta, "manual")
    r["exec_ms"] = ms
    r["auto_algo_reason"] = (
        f"A* selected: guided heuristic faster for specific target {tgt}"
        if algo == "astar" else
        f"Dijkstra selected: exhaustive search for hub destination {tgt}"
    )
    return jsonify(r)

@app.route("/api/dispatch", methods=["POST"])
def dispatch():
    """
    Emergency Action Tiles — algorithm pre-selected per emergency type:
      fire     → Dijkstra → nearest water_src  (exhaustive guarantee)
      medical  → A*       → CLIN               (speed via heuristic)
      security → Dijkstra → GATE               (full scan, safe evacuation)
    """
    data = request.get_json()
    etype  = data.get("type","").lower()
    source = data.get("source","").upper()
    if source not in nodes: return jsonify({"error": f"Invalid source: {source}"}), 400

    graph, meta = build_graph()

    if etype == "fire":
        best, path, dist, graph, meta = find_nearest_resource(source, "water_src")
        if not path: return jsonify({"error": "No water source reachable"}), 404
        _, _, steps = dijkstra(source, best, graph)
        r = build_response("dijkstra", path, dist, steps, graph, meta, "fire")
        r["auto_algo_reason"] = "Dijkstra: exhaustive flood guarantees shortest route to water source"

    elif etype == "medical":
        path, dist, steps = astar(source, "CLIN", graph)
        if not path: return jsonify({"error": "No path to Health Centre"}), 404
        r = build_response("astar", path, dist, steps, graph, meta, "medical")
        r["auto_algo_reason"] = "A*: heuristic beam guides fastest route to clinic in medical emergency"

    elif etype == "security":
        path, dist, steps = dijkstra(source, "GATE", graph)
        if not path: return jsonify({"error": "No evacuation route to gate"}), 404
        r = build_response("dijkstra", path, dist, steps, graph, meta, "security")
        r["lockdown"] = True
        r["auto_algo_reason"] = "Dijkstra: complete graph scan ensures safest evacuation to main gate"

    else:
        return jsonify({"error": "Use type: fire | medical | security"}), 400

    return jsonify(r)

@app.route("/api/resource", methods=["POST"])
def nearest_resource():
    data = request.get_json()
    src  = data.get("source","").upper()
    rtype = data.get("type","med_kit")
    if src not in nodes:   return jsonify({"error": f"Invalid source: {src}"}), 400
    if rtype not in RESOURCE_MAP: return jsonify({"error": "Unknown resource type"}), 400

    candidates = RESOURCE_MAP[rtype]   # O(1) Hash Map lookup
    best, path, dist, graph, meta = find_nearest_resource(src, rtype)
    if not best: return jsonify({"error": "No resource reachable"}), 404

    _, _, steps = dijkstra(src, best, graph)
    r = build_response("dijkstra", path, dist, steps, graph, meta, "resource")
    r.update({"resource_type": rtype, "candidates": candidates,
               "nearest_node": best, "nearest_name": nodes[best]["name"],
               "lookup_note": f"RESOURCE_MAP['{rtype}'] → {candidates} (O(1)). Dijkstra ran to {len(candidates)} candidates."})
    return jsonify(r)

@app.route("/api/roadblock/add", methods=["POST"])
def add_roadblock():
    data = request.get_json()
    src, dst = data.get("src","").upper(), data.get("dst","").upper()
    if src not in nodes or dst not in nodes:
        return jsonify({"error": "Invalid nodes"}), 400
    valid = any((e[0]==src and e[1]==dst) or (e[0]==dst and e[1]==src) for e in BASE_EDGES)
    if not valid: return jsonify({"error": f"No edge between {src} and {dst}"}), 400
    blocked_edges.add(f"{src}-{dst}")
    road = next((e[3] for e in BASE_EDGES if (e[0]==src and e[1]==dst) or (e[0]==dst and e[1]==src)), "Unknown")
    return jsonify({"status":"blocked","edge":f"{src}-{dst}","road":road,"total_blocked":len(blocked_edges)})

@app.route("/api/roadblock/remove", methods=["POST"])
def remove_roadblock():
    data = request.get_json()
    src, dst = data.get("src","").upper(), data.get("dst","").upper()
    removed = False
    for k in (f"{src}-{dst}", f"{dst}-{src}"):
        if k in blocked_edges: blocked_edges.discard(k); removed = True
    if not removed: return jsonify({"error": "Edge not blocked"}), 400
    return jsonify({"status":"unblocked","total_blocked":len(blocked_edges)})

@app.route("/api/roadblock/list")
def list_roadblocks():
    result = []
    for key in blocked_edges:
        parts = key.split("-")
        if len(parts) >= 2:
            s, d = parts[0], parts[1]
            road = next((e[3] for e in BASE_EDGES if (e[0]==s and e[1]==d) or (e[0]==d and e[1]==s)), "Unknown")
            result.append({"key":key,"src":s,"dst":d,"road":road})
    return jsonify({"blocked":result,"count":len(result)})

@app.route("/api/roadblock/clear", methods=["POST"])
def clear_roadblocks():
    n = len(blocked_edges); blocked_edges.clear()
    return jsonify({"status":"cleared","removed":n})

@app.route("/api/complexity")
def complexity():
    return jsonify({
        "campus": {"nodes": len(nodes), "edges": len(BASE_EDGES), "hostels": 7, "blocked": len(blocked_edges)},
        "algorithms": {
            "dijkstra": {"time":"O(E log V)","space":"O(V+E)","heuristic":None,
                         "use":"Fire + Security — exhaustive correctness",
                         "key":"Edge relaxation: dist[u]+w < dist[v] → update"},
            "astar":    {"time":"O(E log V) guided","space":"O(V+E)",
                         "heuristic":"h(n)=√((x₂-x₁)²+(y₂-y₁)²)×1.5  [admissible]",
                         "use":"Medical + Student navigation — guided speed",
                         "key":"f(n)=g(n)+h(n): balance actual + estimated cost"},
        },
        "structures": {
            "adjacency_list": "Hash Map — O(1) neighbor lookup",
            "min_heap":       "Binary Heap — insert O(log n), extract O(log n)",
            "resource_map":   "Hash Map — O(1) resource type lookup",
        },
        "eta": {"formula":"ETA = distance / 1.8 m/s","speed_mps":AVG_SPEED_MPS},
    })


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║  🚨  AMRITA EMERGENCY GPS — Backend v4.1               ║")
    print("║      22 Real Campus Nodes · Real Hostel Names           ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  Girls: Mythreyi · Gargi · Adithi Bhavanam             ║")
    print("║  Boys : Vasishta · Agasthya · Nachiketas · Vyasa        ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  POST /api/pathfind    Dijkstra / A* (auto-select)      ║")
    print("║  POST /api/dispatch    fire | medical | security        ║")
    print("║  POST /api/resource    Nearest fire_ext / med_kit       ║")
    print("║  GET  /api/complexity  Full DSA complexity table        ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print("║  📡  http://localhost:5000                              ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()
    app.run(debug=True, port=5000)
