import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from utils.db import get_db_connection, execute_query
from PIL import Image, ImageDraw
import os
import base64
from io import BytesIO

# Verificar si el usuario está logueado
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.warning("Por favor, inicia sesión primero.")
    st.stop()

st.title("Registro de Corners")

# Inicializar variables de estado si no existen
if 'posiciones_defensivas' not in st.session_state:
    st.session_state.posiciones_defensivas = {}
if 'roles_defensivos' not in st.session_state:
    st.session_state.roles_defensivos = {}
if 'posiciones_ofensivas' not in st.session_state:
    st.session_state.posiciones_ofensivas = {}
if 'roles_ofensivos' not in st.session_state:
    st.session_state.roles_ofensivos = {}
if 'temp_coords' not in st.session_state:
    st.session_state.temp_coords = None

# Obtener lista de partidos
partidos = execute_query("""
    SELECT p.id, e1.nombre, e2.nombre, p.fecha 
    FROM partidos p
    JOIN equipos e1 ON p.equipo_local_id = e1.id
    JOIN equipos e2 ON p.equipo_visitante_id = e2.id
    ORDER BY p.fecha DESC
""", as_dict=False)

if not partidos:
    st.warning("No hay partidos registrados. Por favor, registra un partido primero.")
    st.stop()

# Selector de partido
partido_opciones = {f"{p[1]} vs {p[2]} ({p[3]})": p[0] for p in partidos}
partido_seleccionado = st.selectbox("Selecciona un Partido", list(partido_opciones.keys()))
partido_id = partido_opciones[partido_seleccionado]

# Obtener equipos del partido
equipos_partido = execute_query("""
    SELECT e1.id, e1.nombre, e2.id, e2.nombre
    FROM partidos p
    JOIN equipos e1 ON p.equipo_local_id = e1.id
    JOIN equipos e2 ON p.equipo_visitante_id = e2.id
    WHERE p.id = ?
""", (partido_id,), fetch_one=True, as_dict=False)

equipo_local_id, equipo_local_nombre, equipo_visitante_id, equipo_visitante_nombre = equipos_partido

# Selector de equipo que saca el corner
equipo_atacante = st.radio(
    "Equipo que saca el corner",
    [(equipo_local_id, equipo_local_nombre), (equipo_visitante_id, equipo_visitante_nombre)],
    format_func=lambda x: x[1]
)
equipo_defensivo = (equipo_visitante_id, equipo_visitante_nombre) if equipo_atacante[0] == equipo_local_id else (equipo_local_id, equipo_local_nombre)

# Información del corner
col1, col2, col3 = st.columns(3)
with col1:
    minuto = st.number_input("Minuto", min_value=1, max_value=120)
with col2:
    tipo_corner = st.selectbox("Tipo de Corner", ["Derecha", "Izquierda"])
with col3:
    resultado = st.selectbox("Resultado", ["Gol", "Remate a puerta", "Remate fuera", "Despeje", "Falta atacante", "Falta defensiva", "Otro"])

# Función para dibujar un campo con las posiciones marcadas
def draw_field_with_positions(positions, roles, color_map):
    # Cargar la imagen del campo
    try:
        image = Image.open('assets/mediocampo.jpg')
    except FileNotFoundError:
        st.error("No se encontró la imagen del campo en assets/mediocampo.jpg")
        # Crear una imagen verde como respaldo
        image = Image.new('RGB', (600, 400), (50, 200, 50))
    
    # Dimensiones del campo para escalar coordenadas
    field_width, field_height = image.size
    
    # Crear un objeto para dibujar
    draw = ImageDraw.Draw(image)
    
    # Dibujar las posiciones
    for player_id, (x_percent, y_percent) in positions.items():
        # Convertir porcentajes a coordenadas de píxeles
        x = int(x_percent * field_width / 100)
        y = int(y_percent * field_height / 100)
        
        # Obtener el rol y el color correspondiente
        rol = roles.get(player_id, "Desconocido")
        color_rgb = {
            'Zona': (255, 0, 0),      # Rojo
            'Al hombre': (0, 0, 255),  # Azul
            'Poste': (255, 255, 0),    # Amarillo
            'Arriba': (0, 255, 0),     # Verde
            'Lanzador': (128, 0, 128),  # Morado
            'Rematador': (255, 165, 0), # Naranja
            'Bloqueador': (0, 255, 255), # Cian
            'Arrastre': (255, 0, 255),   # Magenta
            'Rechace': (165, 42, 42),    # Marrón
            'Atrás': (128, 128, 128)     # Gris
        }.get(rol, (255, 255, 255))     # Blanco por defecto
        
        # Dibujar círculo para el jugador
        circle_radius = 15
        draw.ellipse((x-circle_radius, y-circle_radius, x+circle_radius, y+circle_radius), 
                     fill=color_rgb, outline=(0, 0, 0))
        
        # Dibujar número del jugador
        player_info = next((j for j in jugadores if j[0] == player_id), None)
        if player_info:
            numero = str(player_info[2])
            # Centrar el texto (aproximado)
            text_x = x - 4 if len(numero) == 1 else x - 7
            draw.text((text_x, y-7), numero, fill=(0, 0, 0))
    
    return image

# Función para convertir imagen a base64 para HTML
def get_image_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Función para crear un mapa de clics sobre la imagen
def create_image_map(image, field_type, jugador_id=None, rol=None):
    img_width, img_height = image.size
    img_base64 = get_image_base64(image)
    
    grid_cols = 30
    grid_rows = 20
    
    # Generar HTML con imagen y mapa de área superpuesto
    html = f"""
    <style>
        .field-container {{
            position: relative;
            width: 100%;
            height: auto;
        }}
        
        .field-image {{
            width: 100%;
            display: block;
        }}
        
        .grid-overlay {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            display: grid;
            grid-template-columns: repeat({grid_cols}, 1fr);
            grid-template-rows: repeat({grid_rows}, 1fr);
            cursor: crosshair;
        }}
        
        .grid-cell {{
            background-color: rgba(255, 255, 255, 0);
            border: 0;
            transition: background-color 0.2s;
        }}
        
        .grid-cell:hover {{
            background-color: rgba(255, 255, 255, 0.2);
        }}
    </style>
    
    <div class="field-container">
        <img src="data:image/png;base64,{img_base64}" alt="Campo de fútbol" class="field-image">
        <div class="grid-overlay" id="grid-{field_type}">
    """
    
    # Crear celdas de la cuadrícula
    for row in range(grid_rows):
        for col in range(grid_cols):
            # Calcular coordenadas en porcentaje
            x_percent = col * (100 / (grid_cols - 1)) if grid_cols > 1 else 50
            y_percent = row * (100 / (grid_rows - 1)) if grid_rows > 1 else 50
            
            html += f"""
            <div class="grid-cell" 
                 onclick="sendCoords({x_percent}, {y_percent}, '{field_type}', '{jugador_id}', '{rol}')">
            </div>
            """
    
    html += """
        </div>
    </div>
    
    <script>
        function sendCoords(x, y, fieldType, jugadorId, rol) {
            // Enviar mensaje al iframe padre con las coordenadas
            const data = {
                x: x,
                y: y,
                field_type: fieldType,
                jugador_id: jugadorId,
                rol: rol
            };
            
            // Guardar en formulario escondido para recuperar
            document.getElementById('x_coord').value = x;
            document.getElementById('y_coord').value = y;
            document.getElementById('field_type').value = fieldType;
            
            // Enviar formulario
            document.getElementById('coord_form').submit();
        }
    </script>
    
    <form id="coord_form" method="post">
        <input type="hidden" id="x_coord" name="x_coord">
        <input type="hidden" id="y_coord" name="y_coord">
        <input type="hidden" id="field_type" name="field_type">
    </form>
    """
    
    return html

# Enfoque alternativo: usar selectores de posición predefinida
def create_position_selector(field_type, jugador_seleccionado, rol):
    # Definir posiciones comunes en el campo
    positions = [
        ("Corner Izquierdo", 4, 6),    # Nueva posición para corner izquierdo
        ("Corner Derecho", 96, 6),     # Nueva posición para corner derecho
        ("Portería", 50, 15), 
        ("Primer Palo", 35, 25), 
        ("Centro Área", 50, 25), 
        ("Segundo Palo", 65, 25),
        ("Frontal Área", 50, 40), 
        ("Medio Izq", 30, 50), 
        ("Medio Centro", 50, 50), 
        ("Medio Der", 70, 50),
        ("Defensa Izq", 25, 75), 
        ("Defensa Centro", 50, 75), 
        ("Defensa Der", 75, 75)
    ]
    
    # Crear 3 columnas
    cols = st.columns(3)
    
    # Distribuir botones en las columnas
    for i, (name, x, y) in enumerate(positions):
        col_idx = i % 3
        with cols[col_idx]:
            if st.button(name, key=f"pos_{field_type}_{i}"):
                if jugador_seleccionado:
                    return (x, y)
    
    # Controles de ajuste fino para posición personalizada
    st.write("O ajusta coordenadas manualmente:")
    col1, col2 = st.columns(2)
    with col1:
        x_pos = st.slider(f"Posición X", 0, 100, 50, 1, key=f"x_{field_type}")
    with col2:
        y_pos = st.slider(f"Posición Y", 0, 100, 50, 1, key=f"y_{field_type}")
    
    if st.button("Usar estas coordenadas", key=f"use_coords_{field_type}"):
        if jugador_seleccionado:
            return (x_pos, y_pos)
    
    return None

# Sección para el posicionamiento defensivo
st.subheader(f"Posicionamiento Defensivo ({equipo_defensivo[1]})")

# Obtener jugadores del equipo defensivo
jugadores_defensivos = execute_query("""
    SELECT id, nombre, numero 
    FROM jugadores 
    WHERE equipo_id = ?
    ORDER BY numero
""", (equipo_defensivo[0],), as_dict=False)

if not jugadores_defensivos:
    st.warning(f"No hay jugadores registrados para {equipo_defensivo[1]}. Registra jugadores primero.")
    st.stop()

# Variable global para todos los jugadores (usada en la función draw_field_with_positions)
jugadores = jugadores_defensivos.copy()

# Crear una columna para la selección del jugador y otra para el campo
col_def1, col_def2 = st.columns([1, 3])

with col_def1:
    st.write("Selecciona un jugador y su rol")
    jugador_seleccionado_def = st.selectbox(
        "Jugador",
        jugadores_defensivos,
        format_func=lambda x: f"{x[2]} - {x[1]}",
        key="jugador_def"
    )
    rol_defensivo = st.selectbox(
        "Rol Defensivo",
        ["Zona", "Al hombre", "Poste", "Arriba"],
        key="rol_def"
    )
    
    # Mostrar jugadores ya posicionados
    st.write("Jugadores posicionados:")
    for jug_id, pos in st.session_state.posiciones_defensivas.items():
        jug = next((j for j in jugadores_defensivos if j[0] == jug_id), None)
        if jug:
            st.write(f"{jug[2]} - {jug[1]}: {st.session_state.roles_defensivos.get(jug_id, 'N/A')} ({pos[0]:.1f}, {pos[1]:.1f})")
    
    if st.button("Reiniciar Posiciones Defensivas"):
        st.session_state.posiciones_defensivas = {}
        st.session_state.roles_defensivos = {}
        st.rerun()

with col_def2:
    # Dibujar campo con posiciones actuales
    field_image_def = draw_field_with_positions(
        st.session_state.posiciones_defensivas, 
        st.session_state.roles_defensivos,
        {
            'Zona': 'red',
            'Al hombre': 'blue',
            'Poste': 'yellow',
            'Arriba': 'green'
        }
    )
    
    # Mostrar la imagen y usar enfoque de selector de posición predefinida
    st.image(field_image_def, use_column_width=True)
    
    selected_pos = create_position_selector("def", jugador_seleccionado_def, rol_defensivo)
    
    if selected_pos:
        if jugador_seleccionado_def:
            jugador_id = jugador_seleccionado_def[0]
            st.session_state.posiciones_defensivas[jugador_id] = selected_pos
            st.session_state.roles_defensivos[jugador_id] = rol_defensivo
            st.success(f"Jugador {jugador_seleccionado_def[2]} añadido en posición ({selected_pos[0]}, {selected_pos[1]})")
            st.rerun()

# Sección para el posicionamiento ofensivo
st.subheader(f"Posicionamiento Ofensivo ({equipo_atacante[1]})")

# Obtener jugadores del equipo ofensivo
jugadores_ofensivos = execute_query("""
    SELECT id, nombre, numero 
    FROM jugadores 
    WHERE equipo_id = ?
    ORDER BY numero
""", (equipo_atacante[0],), as_dict=False)

if not jugadores_ofensivos:
    st.warning(f"No hay jugadores registrados para {equipo_atacante[1]}. Registra jugadores primero.")
    st.stop()

# Actualizar la variable global para incluir jugadores ofensivos
jugadores.extend(jugadores_ofensivos)

# Crear una columna para la selección del jugador y otra para el campo
col_of1, col_of2 = st.columns([1, 3])

with col_of1:
    st.write("Selecciona un jugador y su rol")
    jugador_seleccionado_of = st.selectbox(
        "Jugador",
        jugadores_ofensivos,
        format_func=lambda x: f"{x[2]} - {x[1]}",
        key="jugador_of"
    )
    rol_ofensivo = st.selectbox(
        "Rol Ofensivo",
        ["Lanzador", "Rematador", "Bloqueador", "Arrastre", "Rechace", "Atrás"],
        key="rol_of"
    )
    
    # Mostrar jugadores ya posicionados
    st.write("Jugadores posicionados:")
    for jug_id, pos in st.session_state.posiciones_ofensivas.items():
        jug = next((j for j in jugadores_ofensivos if j[0] == jug_id), None)
        if jug:
            st.write(f"{jug[2]} - {jug[1]}: {st.session_state.roles_ofensivos.get(jug_id, 'N/A')} ({pos[0]:.1f}, {pos[1]:.1f})")
    
    if st.button("Reiniciar Posiciones Ofensivas"):
        st.session_state.posiciones_ofensivas = {}
        st.session_state.roles_ofensivos = {}
        st.rerun()

with col_of2:
    # Dibujar campo con posiciones actuales
    field_image_of = draw_field_with_positions(
        st.session_state.posiciones_ofensivas, 
        st.session_state.roles_ofensivos,
        {
            'Lanzador': 'purple',
            'Rematador': 'orange',
            'Bloqueador': 'cyan',
            'Arrastre': 'magenta',
            'Rechace': 'brown',
            'Atrás': 'gray'
        }
    )
    
    # Mostrar la imagen y usar enfoque de selector de posición predefinida
    st.image(field_image_of, use_column_width=True)
    
    selected_pos = create_position_selector("of", jugador_seleccionado_of, rol_ofensivo)
    
    if selected_pos:
        if jugador_seleccionado_of:
            jugador_id = jugador_seleccionado_of[0]
            st.session_state.posiciones_ofensivas[jugador_id] = selected_pos
            st.session_state.roles_ofensivos[jugador_id] = rol_ofensivo
            st.success(f"Jugador {jugador_seleccionado_of[2]} añadido en posición ({selected_pos[0]}, {selected_pos[1]})")
            st.rerun()

# Botón para guardar el corner
if st.button("Guardar Corner"):
    if not st.session_state.posiciones_defensivas or not st.session_state.posiciones_ofensivas:
        st.error("Debes posicionar al menos un jugador en cada equipo")
    else:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Insertar el corner
            cursor.execute("""
                INSERT INTO corners (partido_id, equipo_id, minuto, tipo, resultado)
                VALUES (?, ?, ?, ?, ?)
            """, (partido_id, equipo_atacante[0], minuto, tipo_corner, resultado))
            corner_id = cursor.lastrowid
            
            # Insertar posiciones defensivas
            for jug_id, (x, y) in st.session_state.posiciones_defensivas.items():
                cursor.execute("""
                    INSERT INTO posiciones_jugadores (corner_id, jugador_id, equipo_id, x, y, rol, tipo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (corner_id, jug_id, equipo_defensivo[0], x, y, st.session_state.roles_defensivos.get(jug_id), "Defensivo"))
            
            # Insertar posiciones ofensivas
            for jug_id, (x, y) in st.session_state.posiciones_ofensivas.items():
                cursor.execute("""
                    INSERT INTO posiciones_jugadores (corner_id, jugador_id, equipo_id, x, y, rol, tipo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (corner_id, jug_id, equipo_atacante[0], x, y, st.session_state.roles_ofensivos.get(jug_id), "Ofensivo"))
            
            conn.commit()
            st.success("Corner registrado correctamente")
            
            # Limpiar posiciones para un nuevo registro
            st.session_state.posiciones_defensivas = {}
            st.session_state.roles_defensivos = {}
            st.session_state.posiciones_ofensivas = {}
            st.session_state.roles_ofensivos = {}
            st.rerun()
            
        except Exception as e:
            conn.rollback()
            st.error(f"Error al guardar el corner: {e}")
        finally:
            conn.close()