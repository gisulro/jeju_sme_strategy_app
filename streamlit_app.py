import streamlit as st, sys, os, platform, pkgutil
st.title("Env check")
st.write("Python:", platform.python_version())
st.write("CWD:", os.getcwd())
st.write("Files:", os.listdir())
def has(mod): return pkgutil.find_loader(mod) is not None
st.write("plotly installed?", has("plotly"))
st.write("graphviz installed?", has("graphviz"))
st.write("pandas installed?", has("pandas"))
st.write("dateutil installed?", has("dateutil"))
st.success("If you see this, the app boots OK.")
