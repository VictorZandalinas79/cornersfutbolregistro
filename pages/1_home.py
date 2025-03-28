import streamlit as st
import sqlite3
import hashlib
from utils.auth import login_user, register_user

def make_hashed_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

st.title("Bienvenido al Sistema de Análisis de Corners")

# Crear pestañas para login y registro
tab1, tab2 = st.tabs(["Login", "Registro"])

with tab1:
    st.header("Iniciar Sesión")
    username = st.text_input("Usuario", key="login_username")
    password = st.text_input("Contraseña", type="password", key="login_password")
    
    if st.button("Iniciar Sesión"):
        if login_user(username, password):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Bienvenido, {username}!")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")

with tab2:
    st.header("Registrarse")
    new_username = st.text_input("Nuevo Usuario", key="reg_username")
    new_password = st.text_input("Nueva Contraseña", type="password", key="reg_password")
    confirm_password = st.text_input("Confirmar Contraseña", type="password", key="confirm_password")
    
    if st.button("Registrarse"):
        if new_password != confirm_password:
            st.error("Las contraseñas no coinciden")
        elif register_user(new_username, new_password):
            st.success("Usuario registrado correctamente. Ahora puedes iniciar sesión.")
        else:
            st.error("El nombre de usuario ya existe")

# Comprobar si el usuario está logueado
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    st.write(f"Has iniciado sesión como {st.session_state.username}")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()
else:
    st.warning("Por favor, inicia sesión para acceder a todas las funcionalidades.")