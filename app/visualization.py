"""Plotly visualizations for the CAN dashboard."""
from __future__ import annotations
import plotly.graph_objects as go
from .can_network import CANNetwork

COLORS = ["#38bdf8", "#a78bfa", "#34d399", "#fbbf24", "#fb7185", "#22d3ee", "#c084fc", "#4ade80", "#f97316", "#e879f9"]


def network_figure(network: CANNetwork, route: dict | None = None) -> go.Figure:
    fig = go.Figure()
    ids = sorted(network.peers)
    for index, peer_id in enumerate(ids):
        peer = network.peers[peer_id]
        z = peer.zone
        color = COLORS[index % len(COLORS)]
        fig.add_shape(type="rect", x0=z.x1, y0=z.y1, x1=z.x2, y1=z.y2,
                      line=dict(color="#e2e8f0", width=2), fillcolor=color, opacity=0.35)
        keys = len(peer.data)
        fig.add_annotation(x=z.center[0], y=z.center[1], text=f"<b>{peer_id}</b><br>{keys} key{'s' if keys != 1 else ''}",
                           showarrow=False, font=dict(size=13, color="#f8fafc"), bgcolor="rgba(15,23,42,.72)", borderpad=4)
    if route:
        coords = [network.peers[pid].zone.center for pid in route.get("path", []) if pid in network.peers]
        if coords:
            fig.add_trace(go.Scatter(x=[p[0] for p in coords], y=[p[1] for p in coords], mode="lines+markers",
                                     line=dict(color="#f97316", width=4), marker=dict(size=10, color="#f97316"),
                                     name=f"Route ({route.get('hops', 0)} hops)"))
            fig.frames = [
                go.Frame(
                    name=f"hop-{index}",
                    data=[go.Scatter(
                        x=[p[0] for p in coords[: index + 1]],
                        y=[p[1] for p in coords[: index + 1]],
                        mode="lines+markers",
                        line=dict(color="#f97316", width=4),
                        marker=dict(size=10, color="#f97316"),
                    )],
                    traces=[0],
                )
                for index in range(len(coords))
            ]
        x, y = route["coordinate"]
        fig.add_trace(go.Scatter(x=[x], y=[y], mode="markers", marker=dict(size=16, color="#ef4444", symbol="x"),
                                 name=f"Target ({x:.1f}, {y:.1f})"))
    animation_controls = []
    if route and route.get("path"):
        animation_controls = [{
            "type": "buttons", "showactive": False, "x": 0.02, "y": 1.08,
            "xanchor": "left", "yanchor": "top", "direction": "right",
            "buttons": [
                {"label": "▶ Play route", "method": "animate", "args": [None, {"frame": {"duration": 650, "redraw": True}, "transition": {"duration": 250}, "fromcurrent": True}]},
                {"label": "⏸ Pause", "method": "animate", "args": [[None], {"frame": {"duration": 0, "redraw": False}, "mode": "immediate"}]},
            ],
        }]
    fig.update_layout(height=500, margin=dict(l=18, r=18, t=48, b=24), paper_bgcolor="#0f172a", plot_bgcolor="#0f172a",
                      font=dict(color="#e2e8f0"), xaxis=dict(range=[0, 100], dtick=10, title="X coordinate", gridcolor="#334155", scaleanchor="y"),
                      yaxis=dict(range=[0, 100], dtick=10, title="Y coordinate", gridcolor="#334155"), legend=dict(orientation="h", y=-0.12), updatemenus=animation_controls)
    return fig
