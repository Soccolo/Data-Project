"""Streamlit UI flows for the Dara PoC.

``dara/`` is the domain + AI library; ``flows/`` is the Streamlit presentation
layer that drives it. Each flow is a ``render()`` function called by ``app.py``
based on ``st.session_state['view']``.
"""
