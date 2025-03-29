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

# CSS personalizado para un diseño más moderno
st.markdown("""
<style>
    /* Fuentes y estilos generales */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Banner principal */
    .banner {
        width: 100%;
        margin-bottom: 2rem;
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Estilo para tarjetas de contenido */
    .content-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
    }
    
    /* Estilo para títulos */
    h1, h2, h3 {
        color: #1e3a8a;
        font-weight: 700;
    }
    
    /* Estilo para párrafos */
    p {
        font-size: 1.1rem;
        line-height: 1.6;
        color: #4b5563;
    }
    
    /* Estilo para la barra lateral */
    [data-testid=stSidebar] {
        background-image: linear-gradient(180deg, #1e3a8a, #1e40af);
    }
    
    /* Ajustes para el texto en la barra lateral */
    [data-testid=stSidebar] [data-testid=stMarkdownContainer] p,
    [data-testid=stSidebar] [data-testid=stHeading],
    [data-testid=stSidebar] [data-baseweb=tab] button p,
    [data-testid=stSidebar] span, 
    [data-testid=stSidebar] a {
        color: white !important;
    }
    
    /* Logo en la barra lateral */
    .sidebar-logo {
        display: block;
        margin: 0 auto 1.5rem auto;
        width: 80%;
        max-width: 150px;
    }
    
    /* Elementos destacados */
    .highlight {
        background-color: #dbeafe;
        padding: 1rem;
        border-left: 4px solid #3b82f6;
        border-radius: 0.25rem;
        margin: 1rem 0;
    }
    
    /* Sección de características */
    .feature-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1rem;
        margin: 2rem 0;
    }
    
    .feature-item {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

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

# Barra lateral con logo
with st.sidebar:
    # Verificar explícitamente si el archivo existe
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, width=150)
    else:
        st.error(f"Logo no encontrado en {logo_path}")
        st.write("⚽ Análisis de Corners")
    
    st.markdown("---")
    st.markdown('<p style="color: white; font-weight: bold;">Selecciona una página arriba.</p>', unsafe_allow_html=True)

# Banner principal
banner_path = "assets/banner.png"
if os.path.exists(banner_path):
    st.image(banner_path, use_container_width=True)  # Reemplazado use_column_width por use_container_width
else:
    st.error(f"Banner no encontrado en {banner_path}")
    st.title("Análisis de Corners")

# Contenido principal
st.markdown('<div class="content-card">', unsafe_allow_html=True)
st.markdown("## Bienvenido a la aplicación de Análisis de Corners de Fútbol")
st.markdown("""
Esta aplicación te permite registrar, analizar y visualizar el posicionamiento de los jugadores durante los saques de esquina (corners) en partidos de fútbol. Es una herramienta diseñada para entrenadores, analistas tácticos y profesionales que buscan optimizar las estrategias a balón parado.
""")

st.markdown('<div class="highlight">', unsafe_allow_html=True)
st.markdown("""
**Con esta aplicación podrás:**
* Registrar equipos, jugadores y partidos
* Documentar el posicionamiento exacto de cada jugador en los corners
* Analizar patrones ofensivos y defensivos
* Visualizar estadísticas detalladas por equipo y jugador
""")
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Secciones de la aplicación
st.markdown('<div class="content-card">', unsafe_allow_html=True)
st.markdown("## Secciones principales")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 📋 Registro
    
    Permite registrar y gestionar:
    * Equipos
    * Jugadores
    * Partidos
    
    Base fundamental para el análisis posterior.
    """)

with col2:
    st.markdown("""
    ### 🎯 Corners
    
    Registra la ubicación de cada jugador en:
    * Corners ofensivos
    * Corners defensivos
    
    Clasifica por roles específicos y posicionamiento.
    """)

with col3:
    st.markdown("""
    ### 📊 Análisis
    
    Visualiza y analiza datos de:
    * Posicionamiento promedio
    * Efectividad de corners
    * Rendimiento por jugador
    
    Acompañado de gráficos detallados.
    """)

st.markdown('</div>', unsafe_allow_html=True)

# Guía de inicio rápido
st.markdown('<div class="content-card">', unsafe_allow_html=True)
st.markdown("## Guía de inicio rápido")
st.markdown("""
1. **Paso 1**: Comienza registrando equipos en la sección de Registro
2. **Paso 2**: Añade jugadores a cada equipo
3. **Paso 3**: Crea partidos entre los equipos
4. **Paso 4**: Registra los corners y posicionamiento de jugadores
5. **Paso 5**: Explora los análisis y visualizaciones

Usa el menú lateral para navegar entre las diferentes secciones de la aplicación y comenzar a registrar datos.
""")
st.markdown('</div>', unsafe_allow_html=True)

# Pie de página
st.markdown('<div style="text-align: center; margin-top: 2rem; color: #9ca3af; font-size: 0.8rem;">', unsafe_allow_html=True)
st.markdown('© 2025 Análisis de Corners | Victor Zandalinas', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)