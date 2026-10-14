from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import streamlit as st

from app.can_network import CANNetwork
from app.utils import format_coord, init_state
from app.visualization import network_figure

st.set_page_config(
    page_title="CAN Lab | Overlay Network Simulator",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
:root { --navy:#0b1220; --panel:#111c2f; --panel2:#16243d; --line:#263957; --muted:#93a4bd; --cyan:#38bdf8; --green:#34d399; --amber:#fbbf24; }
[data-testid="stAppViewContainer"] { background: radial-gradient(circle at 75% -20%, #1b3154 0, #0b1220 45%); }
[data-testid="stSidebar"] { background: #0e1829; border-right: 1px solid #21324e; }
.block-container { max-width: 1450px; padding: 1.25rem 1.75rem 2.5rem; }
.hero { border:1px solid #2b466b; border-radius:18px; padding:1.25rem 1.5rem; background:linear-gradient(120deg,rgba(21,43,72,.95),rgba(16,29,51,.94)); box-shadow:0 14px 40px rgba(0,0,0,.16); }
.hero-kicker { color:#60a5fa; font-size:.74rem; font-weight:700; letter-spacing:.16em; text-transform:uppercase; }
.hero h1 { color:#f8fafc; font-size:2.05rem; margin:.35rem 0 .3rem; letter-spacing:-.045em; }
.hero p { color:#b4c1d4; margin:0; font-size:.94rem; max-width:780px; }
.section-title { color:#f8fafc; font-size:1.2rem; font-weight:700; margin:.4rem 0 .2rem; }
.section-subtitle { color:var(--muted); font-size:.88rem; margin-bottom:.9rem; }
.metric-card { border:1px solid var(--line); background:rgba(17,28,47,.78); border-radius:12px; padding:.7rem .85rem; min-height:78px; box-shadow:0 5px 16px rgba(0,0,0,.1); }
.metric-label { color:#91a3bd; font-size:.76rem; text-transform:uppercase; letter-spacing:.08em; }
.metric-value { color:#f8fafc; font-size:1.45rem; font-weight:750; margin-top:.18rem; }
.status-pill { display:inline-block; border-radius:999px; padding:.22rem .65rem; font-size:.75rem; font-weight:700; letter-spacing:.03em; }
.status-good { color:#86efac; background:rgba(34,197,94,.13); border:1px solid rgba(34,197,94,.28); }
.status-warn { color:#fde68a; background:rgba(245,158,11,.13); border:1px solid rgba(245,158,11,.28); }
.info-card { border:1px solid var(--line); background:rgba(17,28,47,.55); border-radius:14px; padding:1rem 1.05rem; color:#cbd5e1; }
.info-card strong { color:#f8fafc; }
[data-testid="stMetric"] { background:transparent; }
[data-testid="stTabs"] button { font-weight:650; font-size:.84rem; }
[data-testid="stTabs"] [role="tablist"] { gap:.15rem; border-bottom:1px solid #263957; }
[data-testid="stTabs"] button[aria-selected="true"] { color:#7dd3fc; }
.stButton button { border-radius:9px; font-weight:650; min-height:2.45rem; }
[data-testid="stSidebar"] .stButton button { min-height:2.25rem; }
[data-testid="stSidebar"] h2 { font-size:1.25rem; margin-bottom:.1rem; }
[data-testid="stSidebar"] h3 { font-size:.9rem; text-transform:uppercase; letter-spacing:.08em; color:#cbd5e1; }
[data-testid="stSidebar"] hr { border-color:#21324e; margin:1rem 0; }
@media (max-width: 900px) { .block-container { padding:1rem .85rem 2rem; } .hero h1 { font-size:1.6rem; } }
</style>
""",
    unsafe_allow_html=True,
)

init_state()
network: CANNetwork = st.session_state.network


def reset_network(count: int) -> None:
    st.session_state.network = CANNetwork(count)
    st.session_state.last_route = None
    st.session_state.notice = None


def demo_data() -> None:
    examples = {
        "student101": "Student Record — Computer Science",
        "machine-learning.pdf": "Distributed Systems lecture notes",
        "can-research": "CAN routing research paper",
        "faculty-directory": "Network Systems Faculty Directory",
    }
    for key, value in examples.items():
        network.store(key, value)
    st.session_state.notice = f"Loaded {len(examples)} demonstration records."

with st.sidebar:
    st.markdown("## 🌐 CAN Lab")
    st.caption("Content-Addressable Network simulator")
    st.divider()
    st.markdown("### Network setup")
    initial_peers = st.slider("Peers on reset", min_value=4, max_value=16, value=max(4, min(8, len(network.peers))))
    if st.button("Initialize network", width="stretch", type="primary"):
        reset_network(initial_peers)
        st.rerun()
    if st.button("Load demo records", width="stretch"):
        demo_data()
        st.rerun()
    st.divider()
    st.markdown("### Simulation model")
    st.caption("Coordinate space · 100 × 100")
    st.caption("Zone ownership · rectangular partitions")
    st.caption("Neighbors · positive-length shared boundary")
    st.caption("Routing · greedy Manhattan distance")
    st.divider()
    validation_errors = network.validate()
    if validation_errors:
        st.error("Partition needs attention\n\n" + "\n".join(f"• {error}" for error in validation_errors))
    else:
        st.success("Partition valid", icon="✅")
    with st.expander("What is CAN?", expanded=False):
        st.write("CAN stands for Content-Addressable Network. Each peer owns a zone in a virtual coordinate space and stores the keys that map into that zone.")
        st.write("A lookup is forwarded through neighboring peers until it reaches the peer responsible for the target coordinate.")

st.markdown(
    '<div class="hero"><div class="hero-kicker">Distributed systems laboratory</div><h1>CAN Overlay Network Simulator</h1><p>Visualize zone ownership, distributed key-value storage, and greedy lookup routing in a structured peer-to-peer overlay.</p></div>',
    unsafe_allow_html=True,
)

if st.session_state.notice:
    st.success(st.session_state.notice, icon="✅")
    st.session_state.notice = None

stored_keys = sum(len(peer.data) for peer in network.peers.values())
validation_ok = not validation_errors
metric_items = [
    ("Active peers", len(network.peers)),
    ("Stored keys", stored_keys),
    ("Route successes", network.successful_lookups),
    ("Route failures", network.failed_lookups),
    ("Mean hops", f"{network.average_hops:.2f}"),
]
metric_cols = st.columns(len(metric_items))
for column, (label, value) in zip(metric_cols, metric_items):
    column.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)

st.write("")
visual_col, control_col = st.columns([1.5, 1], gap="large")
with visual_col:
    st.markdown('<div class="section-title">Virtual coordinate space</div><div class="section-subtitle">Colored rectangles represent peer-owned zones; the orange path is the most recent lookup.</div>', unsafe_allow_html=True)
    if validation_ok:
        st.markdown('<span class="status-pill status-good">● PARTITION VALID</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-pill status-warn">● VALIDATION REQUIRED</span>', unsafe_allow_html=True)
    if st.session_state.last_route:
        route = st.session_state.last_route
        target_status = "data found" if route.get("found") else "zone reached; key not stored"
        st.info(f"Last lookup · {' → '.join(route['path'])} · {route['hops']} hop(s) · {target_status}", icon="🔎")
    st.plotly_chart(network_figure(network, st.session_state.last_route), width="stretch", config={"displaylogo": False, "scrollZoom": True})
    st.caption("Half-open zone bounds ensure every mapped coordinate has exactly one owner. After a lookup, use the Plotly **Play route** control to replay each hop.")

with control_col:
    st.markdown('<div class="section-title">Network operations</div><div class="section-subtitle">Run the core CAN operations and observe their effect immediately.</div>', unsafe_allow_html=True)
    tab_add, tab_store, tab_search, tab_leave = st.tabs(["Add peer", "Store data", "Lookup", "Peer leave"])

    with tab_add:
        st.markdown("**Peer join**")
        st.caption("A new peer splits the selected zone along its longest dimension.")
        split_id = st.selectbox("Zone to split", sorted(network.peers), key="split_id")
        selected_zone = network.peers[split_id].zone
        st.caption(f"Selected zone: [{selected_zone.x1:.0f}, {selected_zone.x2:.0f}) × [{selected_zone.y1:.0f}, {selected_zone.y2:.0f})")
        custom_id = st.text_input("New peer ID", placeholder="Auto-generated", key="custom_id")
        if st.button("Join network", key="add_btn", width="stretch", type="primary"):
            try:
                new_peer = network.add_peer(custom_id.strip() or None, split_id)
                st.session_state.notice = f"{new_peer.peer_id} joined the network and received a new zone."
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    with tab_store:
        st.markdown("**Distributed key-value storage**")
        st.caption("The same key always maps to the same coordinate and responsible peer.")
        key = st.text_input("Key", placeholder="student101", key="store_key")
        value = st.text_area("Value", placeholder="Student Record", key="store_value", height=80)
        if key.strip():
            preview_point = network.key_to_coordinate(key.strip())
            preview_owner = network.owner_for_key(key.strip())
            st.info(f"Mapping preview: **{format_coord(preview_point)}** → **{preview_owner.peer_id if preview_owner else 'unresolved'}**", icon="📍")
        if st.button("Store record", key="store_btn", width="stretch", type="primary"):
            try:
                point, owner = network.store(key, value)
                st.session_state.notice = f"Record stored on {owner} at {format_coord(point)}."
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        records = [(peer.peer_id, key_name, record, format_coord(network.key_to_coordinate(key_name))) for peer in network.peers.values() for key_name, record in peer.data.items()]
        if records:
            st.dataframe(pd.DataFrame(records, columns=["Owner", "Key", "Value", "Coordinate"]), hide_index=True, width="stretch")
        else:
            st.caption("No records yet. Use Load demo records in the sidebar or add one above.")

    with tab_search:
        st.markdown("**Greedy lookup and route analysis**")
        st.caption("The request moves only through valid neighbors that reduce distance to the target.")
        search_key = st.text_input("Key to look up", placeholder="student101", key="search_key")
        start_peer = st.selectbox("Starting peer", sorted(network.peers), key="start_peer")
        if st.button("Run lookup", key="search_btn", width="stretch", type="primary"):
            if not search_key.strip():
                st.warning("Enter a key first.")
            else:
                result = network.route(search_key.strip(), start_peer)
                st.session_state.last_route = result
                st.rerun()
        if st.session_state.last_route:
            result = st.session_state.last_route
            st.markdown(f"**Route:** `{' → '.join(result['path'])}`")
            st.caption(f"Destination coordinate: {format_coord(result['coordinate'])} · Destination zone: {result['destination'] or 'unresolved'}")
            if result["success"] and result.get("found"):
                st.success(f"Key found on {result['destination']}: {result['value']}", icon="✅")
            elif result["success"]:
                st.warning("The route reached the responsible zone, but this key is not stored in the network.", icon="⚠️")
            else:
                st.error(f"Routing failed: {result['reason']}")

    with tab_leave:
        st.markdown("**Peer departure**")
        st.caption("The simulator merges compatible zones or rebuilds a valid rectangular partition when needed.")
        if len(network.peers) > 1:
            leave_id = st.selectbox("Peer to remove", sorted(network.peers), key="leave_id")
            if st.button("Remove peer safely", key="leave_btn", width="stretch", type="primary"):
                try:
                    result = network.remove_peer(leave_id)
                    st.session_state.last_route = None
                    st.session_state.notice = f"Removed {leave_id}; {result['keys_moved']} record(s) preserved."
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            st.info("At least one peer must remain.")

st.divider()
with st.expander("How to read this simulation", expanded=False):
    guide_cols = st.columns(3)
    guide_cols[0].markdown("**1 · Partition**\n\nEvery peer owns one rectangle. The rectangles must cover the full 100 × 100 space without overlap.")
    guide_cols[1].markdown("**2 · Mapping**\n\nSHA-256 turns each key into an `(x, y)` coordinate. The zone containing that point owns the record.")
    guide_cols[2].markdown("**3 · Routing**\n\nA lookup walks through neighboring zones using Manhattan distance until it reaches the destination zone.")

st.markdown('<div class="section-title">Peer and neighbor topology</div><div class="section-subtitle">This table is the current overlay routing graph derived from zone boundaries.</div>', unsafe_allow_html=True)
peer_rows = []
for peer in sorted(network.peers.values(), key=lambda item: item.peer_id):
    zone = peer.zone
    peer_rows.append({
        "Peer": peer.peer_id,
        "Zone": f"[{zone.x1:.0f}, {zone.x2:.0f}) × [{zone.y1:.0f}, {zone.y2:.0f})",
        "Area": f"{zone.width * zone.height:.0f}",
        "Neighbors": ", ".join(peer.neighbors) or "—",
        "Keys": len(peer.data),
    })
st.dataframe(pd.DataFrame(peer_rows), hide_index=True, width="stretch")

if network.lookup_history:
    with st.expander(f"Lookup history · {len(network.lookup_history)} recent"):
        history = []
        for item in network.lookup_history:
            if not item["success"]:
                status = "Routing failed"
            elif item.get("found"):
                status = "Data found"
            else:
                status = "Zone reached"
            history.append({"Key": item["key"], "Coordinate": format_coord(item["coordinate"]), "Path": " → ".join(item["path"]), "Hops": item["hops"], "Status": status})
        st.dataframe(pd.DataFrame(history), hide_index=True, width="stretch")

st.caption("CAN Lab · Educational simulator for Content-Addressable Networks · Built with Python, Streamlit, and Plotly")
