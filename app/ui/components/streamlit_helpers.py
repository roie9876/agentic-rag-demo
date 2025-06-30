"""
Streamlit Helper Components
===========================
Reusable Streamlit components and utilities.
"""
import streamlit as st


def st_data_editor(*args, **kwargs):
    """
    Wrapper that tries st.data_editor (Streamlit ≥ 1.29) and falls back to
    st.experimental_data_editor for older releases.
    """
    if hasattr(st, "data_editor"):
        return st.data_editor(*args, **kwargs)
    elif hasattr(st, "experimental_data_editor"):
        return st.experimental_data_editor(*args, **kwargs)
    else:
        st.error(
            "⚠️ Your Streamlit version is too old for data‑editor. "
            "Upgrade with:\n\n"
            "    pip install --upgrade streamlit"
        )
        st.stop()


def health_block_component():
    """
    Placeholder for health block functionality.
    This will be replaced with actual health check logic.
    """
    # This would typically show warnings if health checks haven't passed
    pass
