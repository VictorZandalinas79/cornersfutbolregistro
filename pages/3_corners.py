import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from utils.db import get_db_connection, execute_query
from PIL import Image, ImageDraw, ImageColor
import os
import base64
from io import BytesIO
import math

# Verificar si el usuario está logueado
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.warning("Por favor, inicia sesión primero.")
    st.stop()

# Añadir logo y título en la misma línea
logo_path = "assets/logo.png"
if os.path.exists(logo_path):
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.image(logo_path, width=100)
    with col_title:
        st.title("Registro de Corners")
else:
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
if 'punto_caida' not in st.session_state:
    st.session_state.punto_caida = None
if 'zona_caida_nombre' not in st.session_state:
    st.session_state.zona_caida_nombre = None
# Diccionario para almacenar información adicional de corners (no guardada en la BD)
if 'info_corners' not in st.session_state:
    st.session_state.info_corners = {}
    
# Asegurarse de que los diccionarios existen y son del tipo correcto
if not isinstance(st.session_state.posiciones_defensivas, dict):
    st.session_state.posiciones_defensivas = {}
if not isinstance(st.session_state.roles_defensivos, dict):
    st.session_state.roles_defensivos = {}
if not isinstance(st.session_state.posiciones_ofensivas, dict):
    st.session_state.posiciones_ofensivas = {}
if not isinstance(st.session_state.roles_ofensivos, dict):
    st.session_state.roles_ofensivos = {}

# Verificar si existen las columnas necesarias en la tabla corners
def verificar_columnas_corners():
    try:
        # Intentar ejecutar una consulta que use las columnas
        execute_query("""
            SELECT zona_caida, punto_caida FROM corners LIMIT 1
        """)
        return True, True
    except:
        return False, False

# Verificar si las columnas existen (sin mostrar errores)
try:
    has_zona_caida, has_punto_caida = verificar_columnas_corners()
except:
    has_zona_caida, has_punto_caida = False, False

# Mostrar mensaje si las columnas no existen
if not has_zona_caida or not has_punto_caida:
    st.info("""
    Nota: Algunas funcionalidades avanzadas no estarán disponibles en la base de datos.
    La información de trayectoria se mostrará pero no se guardará permanentemente.
    """)

# Diseño más compacto para selectores
col1, col2 = st.columns(2)

with col1:
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

with col2:
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
        format_func=lambda x: x[1],
        horizontal=True
    )
    equipo_defensivo = (equipo_visitante_id, equipo_visitante_nombre) if equipo_atacante[0] == equipo_local_id else (equipo_local_id, equipo_local_nombre)

# Información del corner en una sola fila
col1, col2, col3 = st.columns(3)
with col1:
    minuto = st.number_input("Minuto", min_value=1, max_value=120)
with col2:
    tipo_corner = st.selectbox("Tipo de Corner", ["Derecha", "Izquierda"])
with col3:
    resultado = st.selectbox("Resultado", ["Gol", "Remate a puerta", "Remate fuera", "Despeje", "Falta atacante", "Falta defensiva", "Otro"])

# Definir el punto de origen del corner basado en el tipo
def get_punto_origen(tipo_corner):
    if tipo_corner == "Derecha":
        return (96, 6)  # Esquina derecha
    else:  # "Izquierda"
        return (4, 6)   # Esquina izquierda

# Definir las zonas de referencia para el punto de caída
def get_zonas_referencia(tipo_corner):
    # Las zonas son: Primer Palo, Centro del Área Pequeña, Segundo Palo,
    # Frontal Palo Cercano, Frontal Centro, Frontal Palo Lejano, 
    # Zona de Rechace, Zona en Corto
    
    if tipo_corner == "Derecha":
        # Corner desde la derecha (viendo hacia la portería)
        return {
            "Segundo Palo": (35, 15),           # Primer palo (más cercano al corner)
            "Centro Área Pequeña": (50, 15),   # Centro del área pequeña
            "Primer Palo": (65, 15),          # Segundo palo (más alejado del corner)
            "Frontal Palo Cercano": (35, 30),  # Frontal cerca del primer palo (cercano al lanzamiento)
            "Frontal Centro": (50, 30),        # Frontal centro
            "Frontal Palo Lejano": (65, 30),   # Frontal cerca del segundo palo (lejano al lanzamiento)
            "Zona de Rechace": (50, 45),       # Zona de rechace
            "Zona en Corto": (80, 20)          # Zona en corto (derecha)
        }
    else:  # "Izquierda"
        # Corner desde la izquierda (viendo hacia la portería)
        return {
            "Segundo Palo": (35, 15),           # Primer palo (más cercano al corner)
            "Centro Área Pequeña": (50, 15),   # Centro del área pequeña
            "Primer Palo": (65, 15),          # Segundo palo (más alejado del corner)
            "Frontal Palo Cercano": (35, 30),  # Frontal cerca del primer palo (cercano al lanzamiento)
            "Frontal Centro": (50, 30),        # Frontal centro
            "Frontal Palo Lejano": (65, 30),   # Frontal cerca del segundo palo (lejano al lanzamiento)
            "Zona de Rechace": (50, 45),       # Zona de rechace
            "Zona en Corto": (20, 20)          # Zona en corto (izquierda)
        }

# Función para dibujar una flecha curva convexa entre dos puntos
def draw_curved_arrow(draw, start_point, end_point, width, height, color=(255, 0, 0), width_line=3):
    # Convertir porcentajes a coordenadas de píxeles
    start_x = int(start_point[0] * width / 100)
    start_y = int(start_point[1] * height / 100)
    end_x = int(end_point[0] * width / 100)
    end_y = int(end_point[1] * height / 100)
    
    # Calcular la distancia entre los puntos
    dx = end_x - start_x
    dy = end_y - start_y
    distance = math.sqrt(dx*dx + dy*dy)
    
    try:
        # Determinar los puntos de control para la curva de Bézier cúbica
        # Para una curva convexa, necesitamos dos puntos de control
        
        # Factor de curvatura - ajusta para cambiar la forma de la flecha
        curvature_factor = 0.3  # Reducido para que la curva no sea tan pronunciada
        
        # Coordenadas para los puntos de control
        # Para una curva convexa, ambos puntos de control deben estar "por encima" de la línea recta
        if start_x < end_x:  # Corner desde la izquierda
            control1_x = start_x + dx * 0.33
            control2_x = start_x + dx * 0.66
        else:  # Corner desde la derecha
            control1_x = start_x - abs(dx) * 0.33
            control2_x = start_x - abs(dx) * 0.66
        
        # Altura de la curva - ajusta para hacer la curva más o menos pronunciada
        # Un valor más alto hace que la flecha sea más convexa
        curve_height = distance * curvature_factor
        
        # Los puntos de control deben estar "por encima" de la línea recta
        control1_y = start_y + dy * 0.33 - curve_height
        control2_y = start_y + dy * 0.66 - curve_height
        
        # Asegurarse de que los puntos de control estén dentro de los límites del campo
        control1_x = max(0, min(width, control1_x))
        control1_y = max(0, min(height, control1_y))
        control2_x = max(0, min(width, control2_x))
        control2_y = max(0, min(height, control2_y))
        
        # Generar puntos a lo largo de la curva de Bézier cúbica para dibujar la flecha
        # Usaremos múltiples segmentos con ancho variable para simular una flecha convexa
        segments = 20
        points = []
        widths = []
        
        for i in range(segments + 1):
            t = i / segments
            # Fórmula para curva de Bézier cúbica
            # B(t) = (1-t)³P₀ + 3(1-t)²tP₁ + 3(1-t)t²P₂ + t³P₃
            # Donde P₀ es start, P₃ es end, y P₁, P₂ son los puntos de control
            
            # Coeficientes de Bernstein para t
            coef0 = (1-t)**3
            coef1 = 3 * (1-t)**2 * t
            coef2 = 3 * (1-t) * t**2
            coef3 = t**3
            
            # Calcular punto en la curva
            x = coef0 * start_x + coef1 * control1_x + coef2 * control2_x + coef3 * end_x
            y = coef0 * start_y + coef1 * control1_y + coef2 * control2_y + coef3 * end_y
            
            # Asegurarse de que el punto está dentro de los límites
            x = max(0, min(width, x))
            y = max(0, min(height, y))
            
            points.append((x, y))
            
            # Ancho variable - más ancho en el medio, más estrecho en los extremos
            # Función de ancho sinusoidal para dar un aspecto natural
            # max_width es el ancho máximo en el medio de la flecha
            max_width = width_line * 2
            base_width = width_line
            
            # t=0 y t=1 tendrán ancho base, t=0.5 tendrá ancho máximo
            segment_width = base_width + (max_width - base_width) * math.sin(t * math.pi)
            widths.append(segment_width)
        
        # Dibujar segmentos de la flecha con ancho variable
        for i in range(len(points) - 1):
            segment_width = int(widths[i])
            # Asegurarse de que el ancho sea al menos 1 pixel
            segment_width = max(1, segment_width)
            draw.line([points[i][0], points[i][1], points[i+1][0], points[i+1][1]], 
                     fill=color, width=segment_width)
        
        # Dibujar punta de flecha solo si hay suficientes puntos
        if len(points) >= 2:
            # Usar el penúltimo y último punto para determinar la dirección
            last_point = points[-1]
            prev_point = points[-2]
            
            # Vector de dirección
            dx = last_point[0] - prev_point[0]
            dy = last_point[1] - prev_point[1]
            
            # Normalizar el vector
            mag = math.sqrt(dx*dx + dy*dy)
            if mag != 0:
                dx, dy = dx/mag, dy/mag
            
            # Tamaño de la punta de flecha proporcional al ancho final
            arrow_size = widths[-1] * 3 if len(widths) > 0 else width_line * 3
            
            # Calcular puntos para la punta de flecha
            arrow_point1_x = last_point[0] - arrow_size * (dx + 0.5*dy)
            arrow_point1_y = last_point[1] - arrow_size * (dy - 0.5*dx)
            arrow_point2_x = last_point[0] - arrow_size * (dx - 0.5*dy)
            arrow_point2_y = last_point[1] - arrow_size * (dy + 0.5*dx)
            
            # Asegurarse de que los puntos de la punta están dentro de los límites
            arrow_point1_x = max(0, min(width, arrow_point1_x))
            arrow_point1_y = max(0, min(height, arrow_point1_y))
            arrow_point2_x = max(0, min(width, arrow_point2_x))
            arrow_point2_y = max(0, min(height, arrow_point2_y))
            
            # Dibujar punta de flecha
            draw.polygon([(last_point[0], last_point[1]), 
                          (arrow_point1_x, arrow_point1_y), 
                          (arrow_point2_x, arrow_point2_y)], 
                         fill=color)
    except Exception as e:
        # Si hay algún error en el dibujo de la flecha, al menos dibujamos una línea simple
        draw.line([start_x, start_y, end_x, end_y], fill=color, width=width_line)
        st.error(f"Error al dibujar la flecha curva: {e}")
        
        # Y un círculo en el punto final para indicar el destino
        draw.ellipse((end_x-5, end_y-5, end_x+5, end_y+5), fill=color)

# Función para dibujar el campo con la flecha de trayectoria
def draw_field_with_trajectory(tipo_corner, punto_caida=None):
    # Cargar la imagen del campo
    try:
        image = Image.open('assets/mediocampo.jpg')
    except FileNotFoundError:
        st.error("No se encontró la imagen del campo en assets/mediocampo.jpg")
        # Crear una imagen verde como respaldo
        image = Image.new('RGB', (600, 400), (50, 200, 50))
    
    # Dimensiones del campo
    field_width, field_height = image.size
    
    # Crear un objeto para dibujar
    draw = ImageDraw.Draw(image)
    
    # Obtener el punto de origen según el tipo de corner
    punto_origen = get_punto_origen(tipo_corner)
    
    # Dibujar el punto de origen (lanzamiento del corner)
    origin_x = int(punto_origen[0] * field_width / 100)
    origin_y = int(punto_origen[1] * field_height / 100)
    circle_radius = 5
    draw.ellipse((origin_x-circle_radius, origin_y-circle_radius, 
                  origin_x+circle_radius, origin_y+circle_radius), 
                 fill=(255, 255, 255), outline=(0, 0, 0))
    
    # Si hay un punto de caída seleccionado, dibujar la flecha
    if punto_caida:
        # Asegurarse de que el punto de caída esté dentro de los límites del campo (0-100%)
        safe_punto_caida = (
            max(0, min(100, punto_caida[0])),  # Limitar X entre 0 y 100
            max(0, min(100, punto_caida[1]))   # Limitar Y entre 0 y 100
        )
        
        # Si el punto original estaba fuera de los límites, mostrar un mensaje
        if safe_punto_caida != punto_caida:
            st.warning("El punto de caída ha sido ajustado para que esté dentro del campo.")
            
        draw_curved_arrow(draw, punto_origen, safe_punto_caida, field_width, field_height)
        
        # Dibujar el punto de caída
        target_x = int(safe_punto_caida[0] * field_width / 100)
        target_y = int(safe_punto_caida[1] * field_height / 100)
        draw.ellipse((target_x-circle_radius, target_y-circle_radius, 
                      target_x+circle_radius, target_y+circle_radius), 
                     fill=(255, 0, 0), outline=(0, 0, 0))
    
    return image

# Sección para seleccionar el punto de caída
st.markdown("### Trayectoria del Corner")

# Obtener las zonas de referencia
zonas_referencia = get_zonas_referencia(tipo_corner)

# Mostrar campo con la flecha de trayectoria
col_tray_img, col_tray_sel = st.columns([3, 1])

with col_tray_img:
    # Dibujar campo con trayectoria
    field_image_tray = draw_field_with_trajectory(tipo_corner, st.session_state.punto_caida)
    st.image(field_image_tray, use_container_width=True, caption="Trayectoria del balón")

# En la sección de selección de zona de caída (reemplaza este bloque):
with col_tray_sel:
    # Selector de zona de referencia para el punto de caída
    zonas_options = [
        "Primer Palo", 
        "Centro Área Pequeña", 
        "Segundo Palo",
        "Frontal Palo Cercano", 
        "Frontal Centro", 
        "Frontal Palo Lejano",
        "Zona de Rechace", 
        "Zona en Corto"
    ]
    
    zona_seleccionada = st.selectbox(
        "Zona de caída del balón",
        zonas_options,
        index=None,
        placeholder="Elige una zona..."
    )
    
    if zona_seleccionada:
        st.session_state.punto_caida = zonas_referencia[zona_seleccionada]
        st.session_state.zona_caida_nombre = zona_seleccionada
        st.success(f"Trayectoria hacia: {zona_seleccionada}")
        # No es necesario el st.rerun() aquí, lo haremos al final
    
    # Botón para borrar la trayectoria - ahora con una key única
    if st.button("Borrar trayectoria", key="borrar_trayectoria_btn"):
        st.session_state.punto_caida = None
        st.session_state.zona_caida_nombre = None
        st.rerun()  # Este rerun es suficiente para actualizar la imagen

# Controles de ajuste fino para el punto de caída
with st.expander("Ajuste fino del punto de caída"):
    col1, col2 = st.columns(2)
    with col1:
        ajuste_x = st.slider("Posición X", 0, 100, 
                             int(st.session_state.punto_caida[0]) if st.session_state.punto_caida else 50, 
                             1, key="ajuste_x_caida")
    with col2:
        ajuste_y = st.slider("Posición Y", 0, 100, 
                             int(st.session_state.punto_caida[1]) if st.session_state.punto_caida else 30, 
                             1, key="ajuste_y_caida")
    
    if st.button("Usar coordenadas personalizadas"):
        st.session_state.punto_caida = (ajuste_x, ajuste_y)
        st.session_state.zona_caida_nombre = "Personalizada"
        st.success("Punto de caída ajustado manualmente")
        st.rerun()

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
    
    # Verificar si hay jugadores para dibujar
    if not positions or not roles:
        return image
    
    # Dibujar las posiciones
    for player_id, (x_percent, y_percent) in positions.items():
        # Convertir porcentajes a coordenadas de píxeles
        x = int(x_percent * field_width / 100)
        y = int(y_percent * field_height / 100)
        
        # Obtener el rol y el color correspondiente
        rol = roles.get(player_id, "Desconocido")
        color_dict = {
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
        }
        color_rgb = color_dict.get(rol, (255, 255, 255))  # Blanco por defecto
        
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

# Enfoque de posición predefinida para layout más compacto
def create_position_selector(field_type, jugador_seleccionado, rol):
    # Verificar si hay un jugador seleccionado
    if not jugador_seleccionado:
        st.warning("Selecciona un jugador primero")
        return None
    
    # Definir posiciones comunes en el campo
    positions = [
        ("Corner Izq", 4, 6),
        ("Corner Der", 96, 6),
        ("Portería", 50, 15), 
        ("1er Palo", 35, 25),
        ("2do Palo", 65, 25), 
        ("Punto Penalti", 50, 30), 
        ("Área pequeña", 50, 20),
        ("Frontal", 50, 40), 
        ("Med. Cen", 50, 50),
        ("Med. Izq", 30, 50), 
        ("Med. Der", 70, 50),
        ("Def. Izq", 25, 75), 
        ("Def. Cen", 50, 75), 
        ("Def. Der", 75, 75)
    ]
    
    # Dividir en múltiples filas para ahorrar espacio vertical
    st.write("Posiciones predefinidas:")
    
    # Crear botones en una disposición de 4 columnas
    cols = st.columns(4)
    
    for i, (name, x, y) in enumerate(positions):
        col_index = i % 4
        with cols[col_index]:
            if st.button(name, key=f"pos_{field_type}_{i}"):
                return (x, y)
    
    # Controles de ajuste fino para posición personalizada
    with st.expander("Ajuste fino de posición"):
        col1, col2 = st.columns(2)
        with col1:
            x_pos = st.slider(f"Posición X", 0, 100, 50, 1, key=f"x_{field_type}")
        with col2:
            y_pos = st.slider(f"Posición Y", 0, 100, 50, 1, key=f"y_{field_type}")
        
        if st.button("Usar coordenadas", key=f"use_coords_{field_type}"):
            return (x_pos, y_pos)
    
    return None

# Layout para posicionamiento de jugadores
st.markdown("### Posicionamiento de Jugadores")

# Crear una fila con dos columnas para ambos equipos
col_def, col_of = st.columns(2)

# Sección para el posicionamiento defensivo
with col_def:
    st.subheader(f"Defensivo ({equipo_defensivo[1]})")

    # Obtener jugadores del equipo defensivo
    jugadores_defensivos = execute_query("""
        SELECT id, nombre, numero 
        FROM jugadores 
        WHERE equipo_id = ?
        ORDER BY numero
    """, (equipo_defensivo[0],), as_dict=False)

    if not jugadores_defensivos:
        st.warning(f"No hay jugadores registrados.")
        st.stop()

    # Variable global para todos los jugadores (usada en la función draw_field_with_positions)
    jugadores = jugadores_defensivos.copy()

    # Selector de jugador y rol
    col_jug_def, col_rol_def = st.columns(2)
    
    with col_jug_def:
        jugador_seleccionado_def = st.selectbox(
            "Jugador",
            jugadores_defensivos,
            format_func=lambda x: f"{x[2]} - {x[1]}",
            key="jugador_def"
        )
    
    with col_rol_def:
        rol_defensivo = st.selectbox(
            "Rol",
            ["Zona", "Al hombre", "Poste", "Arriba"],
            key="rol_def"
        )
    
    # Dibujar campo con posiciones actuales (más pequeño)
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
    st.image(field_image_def, use_container_width=True)
    
    selected_pos = create_position_selector("def", jugador_seleccionado_def, rol_defensivo)
    
    if selected_pos:
        if jugador_seleccionado_def:
            jugador_id = jugador_seleccionado_def[0]
            st.session_state.posiciones_defensivas[jugador_id] = selected_pos
            st.session_state.roles_defensivos[jugador_id] = rol_defensivo
            st.success(f"Jugador #{jugador_seleccionado_def[2]} añadido")
            st.rerun()
    
    # Mostrar jugadores ya posicionados en formato compacto
    with st.expander("Jugadores posicionados"):
        for jug_id, pos in st.session_state.posiciones_defensivas.items():
            jug = next((j for j in jugadores_defensivos if j[0] == jug_id), None)
            if jug:
                st.write(f"#{jug[2]} - {jug[1]}: {st.session_state.roles_defensivos.get(jug_id, 'N/A')}")
        
        if st.button("Reiniciar", key="reset_def"):
            st.session_state.posiciones_defensivas = {}
            st.session_state.roles_defensivos = {}
            st.rerun()

# Sección para el posicionamiento ofensivo
with col_of:
    st.subheader(f"Ofensivo ({equipo_atacante[1]})")

    # Obtener jugadores del equipo ofensivo
    jugadores_ofensivos = execute_query("""
        SELECT id, nombre, numero 
        FROM jugadores 
        WHERE equipo_id = ?
        ORDER BY numero
    """, (equipo_atacante[0],), as_dict=False)

    if not jugadores_ofensivos:
        st.warning(f"No hay jugadores registrados.")
        st.stop()

    # Actualizar la variable global para incluir jugadores ofensivos
    jugadores.extend(jugadores_ofensivos)

    # Selector de jugador y rol
    col_jug_of, col_rol_of = st.columns(2)
    
    with col_jug_of:
        jugador_seleccionado_of = st.selectbox(
            "Jugador",
            jugadores_ofensivos,
            format_func=lambda x: f"{x[2]} - {x[1]}",
            key="jugador_of"
        )
    
    with col_rol_of:
        rol_ofensivo = st.selectbox(
            "Rol",
            ["Lanzador", "Rematador", "Bloqueador", "Arrastre", "Rechace", "Atrás"],
            key="rol_of"
        )
    
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
    st.image(field_image_of, use_container_width=True)
    
    selected_pos = create_position_selector("of", jugador_seleccionado_of, rol_ofensivo)
    
    if selected_pos:
        if jugador_seleccionado_of:
            jugador_id = jugador_seleccionado_of[0]
            st.session_state.posiciones_ofensivas[jugador_id] = selected_pos
            st.session_state.roles_ofensivos[jugador_id] = rol_ofensivo
            st.success(f"Jugador #{jugador_seleccionado_of[2]} añadido")
            st.rerun()
    
    # Mostrar jugadores ya posicionados en formato compacto
    with st.expander("Jugadores posicionados"):
        for jug_id, pos in st.session_state.posiciones_ofensivas.items():
            jug = next((j for j in jugadores_ofensivos if j[0] == jug_id), None)
            if jug:
                st.write(f"#{jug[2]} - {jug[1]}: {st.session_state.roles_ofensivos.get(jug_id, 'N/A')}")
        
        if st.button("Reiniciar", key="reset_of"):
            st.session_state.posiciones_ofensivas = {}
            st.session_state.roles_ofensivos = {}
            st.rerun()

# Agregar sección para gestionar los corners registrados
st.markdown("---")
st.markdown("### Gestión de Corners Registrados")

# Reemplaza el bloque que comienza con "# Obtener corners registrados" con este código:

# Obtener corners registrados
try:
    # Consulta básica sin las columnas adicionales
    corners_registrados = execute_query("""
        SELECT c.id, c.minuto, c.tipo, c.resultado, e.nombre as equipo
        FROM corners c
        JOIN equipos e ON c.equipo_id = e.id
        WHERE c.partido_id = ?
        ORDER BY c.minuto
    """, (partido_id,), as_dict=False)  # Cambiado a False para recibir tuplas
except Exception as e:
    st.error(f"Error al obtener corners: {e}")
    corners_registrados = []

if corners_registrados:
    # Convertir tuplas a formato más fácil de usar
    corners_formateados = []
    for corner in corners_registrados:
        # Asumiendo que el orden de los campos es: id, minuto, tipo, resultado, equipo
        corner_dict = {
            'id': corner[0],
            'minuto': corner[1],
            'tipo': corner[2],
            'resultado': corner[3],
            'equipo': corner[4],
            'zona_caida': "No registrada"  # Valor por defecto
        }
        
        # Añadir datos de zona de caída si existen en la sesión
        if corner_dict['id'] in st.session_state.info_corners:
            corner_dict['zona_caida'] = st.session_state.info_corners[corner_dict['id']].get('zona_caida', "No registrada")
        
        corners_formateados.append(corner_dict)
    
    st.subheader("Corners registrados en este partido:")
    
    # Crear una tabla para mostrar los corners
    corner_data = []
    for corner in corners_formateados:
        corner_data.append({
            "ID": corner['id'],
            "Minuto": corner['minuto'],
            "Equipo": corner['equipo'],
            "Tipo": corner['tipo'],
            "Resultado": corner['resultado'],
            "Zona de Caída": corner['zona_caida']
        })
    
    # Mostrar tabla con los datos
    st.dataframe(corner_data)
    
    # Selector para editar o eliminar un corner
    corner_ids = [f"ID: {c['id']} - Min {c['minuto']} - {c['equipo']} ({c['resultado']})" for c in corners_formateados]
    
    col1, col2 = st.columns(2)
    
    with col1:
        corner_seleccionado = st.selectbox(
            "Selecciona un corner:",
            corner_ids,
            index=None,
            placeholder="Elige un corner para editar/eliminar..."
        )
        
        if corner_seleccionado:
            corner_id = int(corner_seleccionado.split(" - ")[0].replace("ID: ", ""))
            st.session_state.corner_seleccionado_id = corner_id
    
    with col2:
        if 'corner_seleccionado_id' in st.session_state:
            col_editar, col_eliminar = st.columns(2)
            
            with col_editar:
                if st.button("Editar", use_container_width=True):
                    st.warning("La funcionalidad de edición está en desarrollo. Por ahora, puedes eliminar el corner y crear uno nuevo.")
            
            with col_eliminar:
                if st.button("Eliminar", use_container_width=True, type="primary"):
                    try:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        
                        # Primero eliminar las posiciones asociadas
                        cursor.execute("""
                            DELETE FROM posiciones_jugadores 
                            WHERE corner_id = ?
                        """, (st.session_state.corner_seleccionado_id,))
                        
                        # Luego eliminar el corner
                        cursor.execute("""
                            DELETE FROM corners 
                            WHERE id = ?
                        """, (st.session_state.corner_seleccionado_id,))
                        
                        conn.commit()
                        
                        # Eliminar de la información adicional en la sesión
                        if st.session_state.corner_seleccionado_id in st.session_state.info_corners:
                            del st.session_state.info_corners[st.session_state.corner_seleccionado_id]
                        
                        st.success(f"Corner #{st.session_state.corner_seleccionado_id} eliminado correctamente")
                        
                        # Limpiar el estado
                        del st.session_state.corner_seleccionado_id
                        
                        # Recargar la página
                        st.rerun()
                        
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Error al eliminar el corner: {e}")
                    finally:
                        conn.close()
else:
    st.info("No hay corners registrados para este partido.")

# Sección de guardado con estilo destacado
st.markdown("---")
st.markdown("""
<style>
.save-button {
    background-color: #4CAF50;
    border: none;
    color: white;
    padding: 15px 32px;
    text-align: center;
    text-decoration: none;
    display: inline-block;
    font-size: 16px;
    margin: 4px 2px;
    cursor: pointer;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

# Centrar el botón de guardado
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("GUARDAR CORNER", key="save_corner", use_container_width=True):
        if not st.session_state.posiciones_defensivas or not st.session_state.posiciones_ofensivas:
            st.error("Debes posicionar al menos un jugador en cada equipo")
        elif not st.session_state.punto_caida:
            st.error("Debes seleccionar un punto de caída del balón")
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                # Insertar el corner con los campos básicos
                cursor.execute("""
                    INSERT INTO corners (partido_id, equipo_id, minuto, tipo, resultado)
                    VALUES (?, ?, ?, ?, ?)
                """, (partido_id, equipo_atacante[0], minuto, tipo_corner, resultado))
                
                corner_id = cursor.lastrowid
                
                # Guardar los datos adicionales en la sesión para usarlos después
                if st.session_state.punto_caida and st.session_state.zona_caida_nombre:
                    punto_caida_str = f"{st.session_state.punto_caida[0]},{st.session_state.punto_caida[1]}"
                    st.session_state.info_corners[corner_id] = {
                        'zona_caida': st.session_state.zona_caida_nombre,
                        'punto_caida': punto_caida_str
                    }
                
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
                st.session_state.punto_caida = None
                st.session_state.zona_caida_nombre = None
                st.rerun()
                
            except Exception as e:
                conn.rollback()
                st.error(f"Error al guardar el corner: {e}")
            finally:
                conn.close()