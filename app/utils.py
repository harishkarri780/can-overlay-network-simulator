import streamlit as st


def format_coord(point):
    return f"({point[0]:.2f}, {point[1]:.2f})"


def init_state():
    from .can_network import CANNetwork
    if "network" not in st.session_state:
        st.session_state.network = CANNetwork(4)
    if "last_route" not in st.session_state:
        st.session_state.last_route = None
    if "notice" not in st.session_state:
        st.session_state.notice = None
