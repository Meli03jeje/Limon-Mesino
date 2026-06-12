import streamlit as st
import pandas as pd
import numpy as np
import folium
from streamlit_folium import st_folium

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="CVRP · Florida Bebidas — Cartago",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Space+Grotesk:wght@500;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main-header {
    background: linear-gradient(135deg, #0d2b55 0%, #1a4a8a 60%, #2e6fbe 100%);
    border-radius: 12px;
    padding: 28px 36px 22px;
    margin-bottom: 28px;
    color: #fff;
}
.main-header h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 4px;
    letter-spacing: -0.5px;
}
.main-header p { margin: 0; font-size: .9rem; opacity: .75; }

.kpi-row { display: flex; gap: 16px; margin-bottom: 24px; flex-wrap: wrap; }
.kpi-card {
    background: #fff;
    border: 1.5px solid #e8edf5;
    border-left: 5px solid #1a4a8a;
    border-radius: 10px;
    padding: 16px 22px;
    flex: 1 1 160px;
    min-width: 140px;
    box-shadow: 0 2px 8px rgba(0,0,0,.05);
}
.kpi-card .val {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2rem;
    font-weight: 700;
    color: #0d2b55;
    line-height: 1;
}
.kpi-card .lbl { font-size: .75rem; color: #6b7a99; text-transform: uppercase; letter-spacing: .06em; margin-top: 4px; }

.sec-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.1rem;
    font-weight: 700;
    color: #0d2b55;
    border-bottom: 2px solid #e8edf5;
    padding-bottom: 8px;
    margin: 20px 0 16px;
}

section[data-testid="stSidebar"] {
    background: #f4f7fc;
    border-right: 1px solid #dde4f0;
}

.badge-ok { background:#22c55e; color:#fff; padding:3px 12px; border-radius:12px; font-size:.8rem; font-weight:600; }
.badge-err { background:#ef4444; color:#fff; padding:3px 12px; border-radius:12px; font-size:.8rem; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────
CANTONS = {
    0: "CD Cartago", 1: "Cartago", 2: "Paraíso", 3: "La Unión",
    4: "Jiménez", 5: "Turrialba", 6: "Alvarado", 7: "Oreamuno", 8: "El Guarco",
}

DEFAULT_DEMAND = {0: 0, 1: 124, 2: 48, 3: 75, 4: 15, 5: 61, 6: 12, 7: 36, 8: 35}

DIST = [
    [0,  0,  9, 10, 34, 34, 20,  6,  6],
    [0,  0,  9, 10, 34, 34, 20,  6,  6],
    [9,  9,  0, 19, 26, 28, 13,  7, 12],
    [10, 10, 19,  0, 45, 43, 29, 14, 11],
    [34, 34, 26, 45,  0, 20, 21, 31, 37],
    [34, 34, 28, 43, 20,  0, 15, 29, 40],
    [20, 20, 13, 29, 21, 15,  0, 14, 25],
    [6,   6,  7, 14, 31, 29, 14,  0, 12],
    [6,   6, 12, 11, 37, 40, 25, 12,  0],
]

# GPS centroids for each canton
COORDS = {
    0: (9.8648, -83.9190),  # CD / Cartago city
    1: (9.8648, -83.9190),
    2: (9.8400, -83.8700),
    3: (9.9000, -83.9900),
    4: (9.7500, -83.7500),
    5: (9.9000, -83.6800),
    6: (9.9300, -83.8500),
    7: (9.9400, -83.8900),
    8: (9.8200, -83.9400),
}

ROUTE_COLORS = [
    "#e63946","#457b9d","#2a9d8f","#e76f51","#8338ec","#fb8500",
    "#06d6a0","#f72585","#023e8a","#80b918","#f4a261","#264653",
    "#c77dff","#90e0ef","#d62828","#3a86ff","#ffbe0b","#fb5607",
    "#4cc9f0","#7209b7","#480ca8","#b5e48c",
]

DEMAND_TABLE = {
    "Nodo": list(range(9)),
    "Cantón": [CANTONS[i] for i in range(9)],
    "Imperial": [0, 62, 24, 37, 7, 31, 6, 18, 17],
    "Pilsen":   [0, 31, 12, 19, 4, 15, 3,  9,  9],
    "Tropical": [0, 31, 12, 19, 4, 15, 3,  9,  9],
    "Total":    [DEFAULT_DEMAND[i] for i in range(9)],
}

# ─────────────────────────────────────────────
# SOLVER — Clarke-Wright + greedy merge
# ─────────────────────────────────────────────

def route_dist(nodes):
    """Round-trip distance: depot -> nodes -> depot."""
    path = [0] + nodes + [0]
    return sum(DIST[path[k]][path[k + 1]] for k in range(len(path) - 1))


def solve_cvrp(demand: dict, capacity: int):
    """
    CVRP solver using Clarke-Wright Savings + greedy slot merging.
    
    Returns list of dicts:
      { 'nodes': [n1, n2, ...], 'deliveries': [(node, pallets), ...], 'load': int, 'km': float }
    
    Constraints enforced:
      1. Flow conservation: every truck that leaves CD returns to CD
      2. Demand satisfaction: sum of deliveries to each canton >= its demand
      3. Capacity: total load per truck <= capacity
    """
    # Step 1: decompose each canton's demand into partial slots (<= capacity)
    slots = []  # list of (canton, pallets)
    for canton in range(1, 9):
        d = demand.get(canton, 0)
        while d > 0:
            take = min(d, capacity)
            slots.append((canton, take))
            d -= take

    # Step 2: start with each slot as its own "route"
    routes = [{"stops": [s], "load": s[1]} for s in slots]

    # Step 3: iteratively merge routes while capacity allows and saving >= 0
    improved = True
    while improved:
        improved = False
        best_saving = -1
        best_i, best_j, best_route = None, None, None

        for i in range(len(routes)):
            for j in range(i + 1, len(routes)):
                ri, rj = routes[i], routes[j]
                if ri["load"] + rj["load"] > capacity:
                    continue

                stops_merged = ri["stops"] + rj["stops"]
                nodes_i = list(dict.fromkeys(n for n, _ in ri["stops"]))
                nodes_j = list(dict.fromkeys(n for n, _ in rj["stops"]))
                nodes_merged = list(dict.fromkeys(n for n, _ in stops_merged))

                d_before = route_dist(nodes_i) + route_dist(nodes_j)
                d_after = route_dist(nodes_merged)
                saving = d_before - d_after

                if saving > best_saving:
                    best_saving = saving
                    best_i, best_j = i, j
                    best_route = {
                        "stops": stops_merged,
                        "load": ri["load"] + rj["load"],
                    }

        if best_i is not None and best_saving >= 0:
            routes[best_i] = best_route
            routes.pop(best_j)
            improved = True

    # Step 4: format results
    result = []
    for r in routes:
        nodes = list(dict.fromkeys(n for n, _ in r["stops"]))
        result.append({
            "nodes": nodes,
            "deliveries": r["stops"],
            "load": r["load"],
            "km": route_dist(nodes),
        })

    # Sort by km descending (longest routes first in display)
    result.sort(key=lambda x: -x["km"])
    return result


def verify_solution(routes, demand, capacity):
    """Returns (demand_ok, capacity_ok, delivered_per_canton)."""
    delivered = {i: 0 for i in range(1, 9)}
    cap_ok = True
    for r in routes:
        for node, pallets in r["deliveries"]:
            delivered[node] += pallets
        if r["load"] > capacity:
            cap_ok = False
    demand_ok = all(delivered[i] >= demand.get(i, 0) for i in range(1, 9))
    return demand_ok, cap_ok, delivered


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Parámetros del modelo")
    st.markdown("---")

    st.markdown("### 🚛 Capacidad de camión")
    cap = st.slider("Pallets por camión", 12, 48, 24, step=1,
                    help="Capacidad máxima por camión (pallets)")

    st.markdown("### 📦 Demanda por cantón (pallets/sem)")
    demand_inputs = {0: 0}
    for i in range(1, 9):
        demand_inputs[i] = st.number_input(
            f"{CANTONS[i]}", min_value=0, max_value=500,
            value=DEFAULT_DEMAND[i], step=1, key=f"d_{i}"
        )

    st.markdown("---")
    run_btn = st.button("▶ Resolver CVRP", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("### 📊 Resumen de entrada")
    total_demand_sidebar = sum(demand_inputs[i] for i in range(1, 9))
    min_trucks_th = int(np.ceil(total_demand_sidebar / cap)) if cap > 0 else 0
    st.metric("Demanda total", f"{total_demand_sidebar} pallets")
    st.metric("Flota mínima teórica", f"{min_trucks_th} camiones")
    st.metric("Capacidad por camión", f"{cap} pallets")

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🚛 CVRP · Florida Bebidas — Provincia de Cartago</h1>
    <p>Optimización de rutas de distribución · Flujos de Redes · II-1122 · UCR Sede Alajuela · I-2026</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# RUN SOLVER
# ─────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result = None

if run_btn:
    with st.spinner("Resolviendo CVRP con Clarke-Wright Savings..."):
        routes = solve_cvrp(demand_inputs, cap)
        st.session_state.result = {
            "routes": routes,
            "demand": dict(demand_inputs),
            "cap": cap,
        }

# ─────────────────────────────────────────────
# RESULTS
# ─────────────────────────────────────────────
if st.session_state.result:
    res = st.session_state.result
    routes = res["routes"]
    demand = res["demand"]
    cap_used = res["cap"]

    demand_ok, cap_ok, delivered = verify_solution(routes, demand, cap_used)
    total_km_val = sum(r["km"] for r in routes)
    total_pallets = sum(r["load"] for r in routes)
    n_routes = len(routes)

    # ── KPIs ──
    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi-card"><div class="val">{n_routes}</div><div class="lbl">Camiones usados</div></div>
        <div class="kpi-card"><div class="val">{total_km_val:.0f} km</div><div class="lbl">Distancia total</div></div>
        <div class="kpi-card"><div class="val">{total_pallets}</div><div class="lbl">Pallets entregados</div></div>
        <div class="kpi-card"><div class="val">{sum(demand[i] for i in range(1,9))}</div><div class="lbl">Demanda total</div></div>
        <div class="kpi-card"><div class="val">{cap_used}</div><div class="lbl">Cap/camión</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Constraint badges ──
    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        b = "badge-ok" if demand_ok else "badge-err"
        st.markdown(f'<span class="{b}">{"✅" if demand_ok else "❌"} Demanda satisfecha</span>', unsafe_allow_html=True)
    with col_b2:
        b = "badge-ok" if cap_ok else "badge-err"
        st.markdown(f'<span class="{b}">{"✅" if cap_ok else "❌"} Capacidad ≤ {cap_used} pallets</span>', unsafe_allow_html=True)
    with col_b3:
        st.markdown('<span class="badge-ok">✅ Conservación de flujo</span>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Two columns: table | map ──
    col_left, col_right = st.columns([1, 1.6], gap="large")

    with col_left:
        st.markdown('<div class="sec-title">📋 Rutas óptimas</div>', unsafe_allow_html=True)
        rows = []
        for idx, r in enumerate(routes):
            path = " → ".join(["CD"] + [CANTONS[n] for n in r["nodes"]] + ["CD"])
            rows.append({
                "Camión": f"#{idx+1}",
                "Ruta": path,
                "Pallets": r["load"],
                "Uso": f"{100*r['load']/cap_used:.0f}%",
                "km": f"{r['km']:.0f}",
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.markdown('<div class="sec-title">✅ Verificación de demanda por cantón</div>', unsafe_allow_html=True)
        verif = []
        for i in range(1, 9):
            d = demand.get(i, 0)
            if d > 0:
                ok = delivered[i] >= d
                verif.append({"Cantón": CANTONS[i], "Demanda": d,
                               "Entregado": delivered[i], "Estado": "✅" if ok else "❌"})
        st.dataframe(pd.DataFrame(verif), use_container_width=True, hide_index=True)

    with col_right:
        st.markdown('<div class="sec-title">🗺️ Mapa de rutas — Cartago</div>', unsafe_allow_html=True)

        m = folium.Map(location=[9.87, -83.85], zoom_start=10, tiles="CartoDB positron")

        for idx, r in enumerate(routes):
            color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]
            full_path = [0] + r["nodes"] + [0]
            coords_path = [COORDS[n] for n in full_path]
            folium.PolyLine(
                locations=coords_path,
                color=color, weight=3.5, opacity=0.85,
                tooltip=f"Camión #{idx+1} | {r['load']} pallets | {r['km']:.0f} km",
            ).add_to(m)

        # Canton markers
        for i, name in CANTONS.items():
            lat, lon = COORDS[i]
            if i == 0:
                folium.Marker(
                    location=[lat, lon],
                    tooltip="⭐ CD Cartago (Depósito)",
                    popup=folium.Popup("<b>⭐ CD Cartago — Depósito</b>", max_width=200),
                    icon=folium.Icon(color="darkblue", icon="star", prefix="fa"),
                ).add_to(m)
            elif demand.get(i, 0) > 0:
                d = demand[i]
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=8 + d // 20,
                    color="#fff", weight=2,
                    fill=True, fill_color="#1a4a8a", fill_opacity=0.85,
                    tooltip=f"{name}: {d} pallets",
                    popup=folium.Popup(
                        f"<b>{name}</b><br>Demanda: {d} pallets<br>Entregado: {delivered.get(i,0)} pallets",
                        max_width=200),
                ).add_to(m)

        # Legend
        legend_html = """<div style="position:fixed;bottom:20px;left:20px;z-index:9999;
            background:white;padding:12px 16px;border-radius:10px;
            box-shadow:0 2px 12px rgba(0,0,0,.18);font-size:11px;
            font-family:Inter,sans-serif;max-width:240px;">
            <b style="font-size:12px;">🚛 Rutas</b><br><br>"""
        for idx, r in enumerate(routes):
            color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]
            names = " → ".join(CANTONS[n][:7] for n in r["nodes"])
            legend_html += f'<span style="background:{color};display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:5px;vertical-align:middle;"></span>#{idx+1}: {names} ({r["km"]:.0f}km)<br>'
        legend_html += "</div>"
        m.get_root().html.add_child(folium.Element(legend_html))

        st_folium(m, width=None, height=540, returned_objects=[])

    # ── Model formulation ──
    st.markdown('<div class="sec-title">🔢 Formulación matemática del modelo CVRP</div>', unsafe_allow_html=True)
    with st.expander("Ver formulación completa", expanded=False):
        st.markdown(r"""
**Conjuntos:**
- $N = \{0, 1, \ldots, 8\}$: nodos (0 = CD depósito, $1..8$ = cantones de Cartago)
- $K$: conjunto de camiones (flota)
- $A = N \times N$: arcos de la red

**Parámetros:**
- $d_{ij}$: distancia (km) entre nodo $i$ y nodo $j$
- $q_i$: demanda del cantón $i$ (pallets/semana)
- $Q$: capacidad del camión (pallets)
- $M$: Big-M (número suficientemente grande)

**Variables de decisión:**
- $x_{ijk} \in \{0,1\}$: 1 si el camión $k$ recorre el arco $(i \to j)$
- $y_{ik} \geq 0$: pallets entregados por el camión $k$ en el cantón $i$

---

**Función objetivo** — minimizar distancia total recorrida:
$$\min Z = \sum_{k \in K} \sum_{(i,j) \in A} d_{ij} \cdot x_{ijk}$$

**Restricciones:**

**R1 — Conservación de flujo** (Camión entra = Camión sale en cada nodo):
$$\sum_{j \in N} x_{jik} = \sum_{j \in N} x_{ijk} \quad \forall i \in N,\; k \in K$$

**R2 — Satisfacción de demanda** (cada cantón recibe al menos su demanda):
$$\sum_{k \in K} y_{ik} \geq q_i \quad \forall i \in N \setminus \{0\}$$

**R3 — Capacidad del camión** (Big-M: limita la cantidad de pallets por camión):
$$\sum_{i \in N} y_{ik} \leq Q \cdot \sum_{j \in N} x_{0jk} \quad \forall k \in K$$

**R4 — Carga solo si visita** (vincula entrega con visita):
$$y_{ik} \leq Q \cdot \sum_{j \in N} x_{ijk} \quad \forall i \in N,\; k \in K$$

**R5 — Eliminación de subtours** (Miller-Tucker-Zemlin):
$$u_{ik} - u_{jk} + Q \cdot x_{ijk} \leq Q - q_j \quad \forall i \neq j,\; i,j \neq 0,\; k \in K$$

---
**Método de solución:** Heurística Clarke-Wright Savings con fusión greedy iterativa.  
Se garantiza: R1 (cada camión sale y regresa al CD), R2 (demanda cubierta), R3-R4 (máx. $Q$ pallets).
        """)

    # ── Detail cards ──
    st.markdown('<div class="sec-title">🗂️ Detalle por camión</div>', unsafe_allow_html=True)
    cols3 = st.columns(3)
    for idx, r in enumerate(routes):
        color = ROUTE_COLORS[idx % len(ROUTE_COLORS)]
        delivery_by_node = {}
        for node, pallets in r["deliveries"]:
            delivery_by_node[node] = delivery_by_node.get(node, 0) + pallets
        stops_html = "".join(
            f"<li>{CANTONS[n]}: <b>{delivery_by_node[n]}</b> pallets</li>"
            for n in r["nodes"]
        )
        path_str = " → ".join(["CD"] + [CANTONS[n] for n in r["nodes"]] + ["CD"])
        with cols3[idx % 3]:
            st.markdown(f"""
            <div style="background:#fff;border:1.5px solid #e8edf5;border-top:4px solid {color};
                        border-radius:10px;padding:14px 16px;margin-bottom:14px;
                        box-shadow:0 2px 8px rgba(0,0,0,.05);">
                <b style="font-size:.93rem;color:#0d2b55;">Camión #{idx+1}</b>
                <span style="float:right;background:{color};color:#fff;font-size:.7rem;
                             padding:2px 8px;border-radius:10px;font-weight:600;">
                    {r['load']}/{cap_used} pallets
                </span>
                <div style="font-size:.73rem;color:#6b7a99;margin:4px 0 6px;">{r['km']:.0f} km · {len(r['nodes'])} parada(s)</div>
                <ul style="margin:0;padding-left:16px;font-size:.77rem;color:#334;line-height:1.7;">{stops_html}</ul>
                <div style="margin-top:8px;font-size:.7rem;color:#999;">
                    Uso: {100*r['load']/cap_used:.0f}%
                </div>
            </div>
            """, unsafe_allow_html=True)

else:
    # Welcome / data preview
    st.info("👈 Ajusta los parámetros en el panel lateral y presiona **▶ Resolver CVRP**.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="sec-title">📊 Demanda inicial por cantón</div>', unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(DEMAND_TABLE), use_container_width=True, hide_index=True)
    with col2:
        st.markdown('<div class="sec-title">📏 Matriz de distancias (km)</div>', unsafe_allow_html=True)
        labels = [f"{i}·{CANTONS[i][:9]}" for i in range(9)]
        st.dataframe(pd.DataFrame(DIST, index=labels, columns=labels), use_container_width=True)

# ── Footer ──
st.markdown("---")
st.markdown(
    '<p style="text-align:center;font-size:.75rem;color:#9aa3b5;">'
    'II-1122 · Flujos de Redes · Prof. David Benavides · UCR Sede Alajuela · I-2026 &nbsp;|&nbsp;'
    ' Modelo CVRP · Clarke-Wright Savings · Florida Bebidas · Planta Río Segundo, Alajuela'
    '</p>',
    unsafe_allow_html=True
)
