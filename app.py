import streamlit as st
import sqlite3
import os

# Configurar la sesión y la página
st.set_page_config(
    page_title="Análisis de Corners",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Crear la base de datos si no existe
if not os.path.exists('data'):
    os.makedirs('data')

conn = sqlite3.connect('data/corners.db')
cursor = conn.cursor()

# Crear tablas si no existen
cursor.execute('''
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE,
    password TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS equipos (
    id INTEGER PRIMARY KEY,
    nombre TEXT UNIQUE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS jugadores (
    id INTEGER PRIMARY KEY,
    nombre TEXT,
    equipo_id INTEGER,
    numero INTEGER,
    FOREIGN KEY (equipo_id) REFERENCES equipos (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS partidos (
    id INTEGER PRIMARY KEY,
    equipo_local_id INTEGER,
    equipo_visitante_id INTEGER,
    fecha TEXT,
    FOREIGN KEY (equipo_local_id) REFERENCES equipos (id),
    FOREIGN KEY (equipo_visitante_id) REFERENCES equipos (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS corners (
    id INTEGER PRIMARY KEY,
    partido_id INTEGER,
    equipo_id INTEGER,
    minuto INTEGER,
    tipo TEXT,
    resultado TEXT,
    FOREIGN KEY (partido_id) REFERENCES partidos (id),
    FOREIGN KEY (equipo_id) REFERENCES equipos (id)
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS posiciones_jugadores (
    id INTEGER PRIMARY KEY,
    corner_id INTEGER,
    jugador_id INTEGER,
    equipo_id INTEGER,
    x REAL,
    y REAL,
    rol TEXT,
    tipo TEXT,
    FOREIGN KEY (corner_id) REFERENCES corners (id),
    FOREIGN KEY (jugador_id) REFERENCES jugadores (id),
    FOREIGN KEY (equipo_id) REFERENCES equipos (id)
)
''')

conn.commit()
conn.close()

# Página principal
st.title("Análisis de Corners")
st.write("Bienvenido a la aplicación para el análisis de corners en fútbol.")
st.write("Navega por las páginas usando el menú lateral.")

st.sidebar.success("Selecciona una página arriba.")