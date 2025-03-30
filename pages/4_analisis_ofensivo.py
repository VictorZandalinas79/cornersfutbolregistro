import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, FancyArrowPatch
from matplotlib.path import Path
import matplotlib.patches as patches
from utils.db import get_db_connection
import os
from PIL import Image
import matplotlib.image as mpimg
import math
import seaborn as sns
from matplotlib.lines import Line2D

# Verificar si el usuario está logueado
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.warning("Por favor, inicia sesión primero.")
    st.stop()

# Función para verificar y actualizar la estructura de la tabla corners si es necesario
def ensure_corner_columns_exist():
    """Asegurar que las columnas zona_caida y punto_caida existen en la tabla corners"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(corners)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # Añadir columna zona_caida si no existe
        if 'zona_caida' not in columns:
            cursor.execute("ALTER TABLE corners ADD COLUMN zona_caida TEXT")
            st.info("Columna zona_caida añadida a la tabla corners")
        
        # Añadir columna punto_caida si no existe
        if 'punto_caida' not in columns:
            cursor.execute("ALTER TABLE corners ADD COLUMN punto_caida TEXT")
            st.info("Columna punto_caida añadida a la tabla corners")
        
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Error al añadir columnas: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# Ejecutar verificación de estructura de tabla
ensure_corner_columns_exist()

# Añadir logo en la parte superior
logo_path = "assets/logo.png"
if os.path.exists(logo_path):
    col_logo, col_title = st.columns([1, 5])
    with col_logo:
        st.image(logo_path, width=100)
    with col_title:
        st.title("Análisis de Posicionamiento Ofensivo")
else:
    st.title("Análisis de Posicionamiento Ofensivo")

# Obtener lista de equipos
conn = get_db_connection()
equipos = conn.execute("SELECT id, nombre FROM equipos").fetchall()
conn.close()

if not equipos:
    st.warning("No hay equipos registrados.")
    st.stop()

# Crear un layout de dos columnas para los selectores
col_equipo, col_jugador = st.columns(2)

with col_equipo:
    # Selector de equipo
    equipo_opciones = {equipo[1]: equipo[0] for equipo in equipos}
    equipo_seleccionado = st.selectbox("Selecciona un Equipo", list(equipo_opciones.keys()))
    equipo_id = equipo_opciones[equipo_seleccionado]

# Obtener corners ofensivos del equipo
conn = get_db_connection()
corners = conn.execute("""
    SELECT c.id, p.fecha, e1.nombre as local, e2.nombre as visitante, c.minuto, c.tipo, c.resultado,
           p.equipo_local_id, p.equipo_visitante_id, c.zona_caida, c.punto_caida
    FROM corners c
    JOIN partidos p ON c.partido_id = p.id
    JOIN equipos e1 ON p.equipo_local_id = e1.id
    JOIN equipos e2 ON p.equipo_visitante_id = e2.id
    WHERE c.equipo_id = ?
    ORDER BY p.fecha DESC
""", (equipo_id,)).fetchall()
conn.close()

if not corners:
    st.warning(f"No hay corners registrados para {equipo_seleccionado}.")
    st.stop()

# Obtener el equipo local para cada partido para usar en la visualización
equipo_local_id = corners[0][7] if corners else None

# Obtener lista de jugadores del equipo para el selector de jugador
conn = get_db_connection()
jugadores = conn.execute("""
    SELECT id, nombre, numero 
    FROM jugadores 
    WHERE equipo_id = ?
    ORDER BY numero
""", (equipo_id,)).fetchall()
conn.close()

with col_jugador:
    if jugadores:
        # Selector de jugador
        jugador_opciones = {f"{j[2]} - {j[1]}": j[0] for j in jugadores}
        jugador_seleccionado = st.selectbox("Selecciona un Jugador", list(jugador_opciones.keys()))
        jugador_id = jugador_opciones[jugador_seleccionado]
    else:
        st.warning(f"No hay jugadores registrados para {equipo_seleccionado}.")
        jugador_id = None

st.info(f"Se encontraron {len(corners)} corners ofensivos para {equipo_seleccionado}")

# Función para crear una flecha convexa
def create_curved_arrow(ax, start_point, end_point, color='red', width=2, label=None, curvature=0.2):
    # Calcular punto medio
    mid_x = (start_point[0] + end_point[0]) / 2
    mid_y = (start_point[1] + end_point[1]) / 2
    
    # Calcular la distancia entre los puntos
    dx = end_point[0] - start_point[0]
    dy = end_point[1] - start_point[1]
    distance = math.sqrt(dx*dx + dy*dy)
    
    # Determinar la dirección de la curva
    if start_point[0] < end_point[0]:  # De izquierda a derecha
        control_x = mid_x
        control_y = mid_y + distance * curvature
    else:  # De derecha a izquierda
        control_x = mid_x
        control_y = mid_y - distance * curvature
    
    # Crear los puntos de la ruta para la flecha
    verts = [
        (start_point[0], start_point[1]),  # Punto inicial
        (control_x, control_y),            # Punto de control
        (end_point[0], end_point[1]),      # Punto final
    ]
    
    codes = [
        Path.MOVETO,
        Path.CURVE3,
        Path.CURVE3,
    ]
    
    path = Path(verts, codes)
    patch = patches.PathPatch(path, facecolor='none', edgecolor=color, lw=width, alpha=0.7)
    ax.add_patch(patch)
    
    # Dibujar punta de flecha
    arrow_length = 0.5
    arrow_width = 0.3
    
    # Calcular la dirección en el punto final
    # Para una curva Bézier cuadrática, la dirección tangente en t=1 es P2-P1
    dx = end_point[0] - control_x
    dy = end_point[1] - control_y
    
    # Normalizar el vector
    mag = math.sqrt(dx*dx + dy*dy)
    if mag != 0:
        dx, dy = dx/mag, dy/mag
    
    # Calcular puntos para la punta de flecha
    arrow_point1_x = end_point[0] - arrow_length * (dx + arrow_width*dy)
    arrow_point1_y = end_point[1] - arrow_length * (dy - arrow_width*dx)
    arrow_point2_x = end_point[0] - arrow_length * (dx - arrow_width*dy)
    arrow_point2_y = end_point[1] - arrow_length * (dy + arrow_width*dx)
    
    # Dibujar la punta de flecha
    ax.fill([end_point[0], arrow_point1_x, arrow_point2_x], 
            [end_point[1], arrow_point1_y, arrow_point2_y], 
            color=color, alpha=0.7)
    
    # Añadir etiqueta en la parte curva de la flecha
    if label:
        # Posicionar la etiqueta en la parte más convexa de la curva
        label_x = control_x
        label_y = control_y
        
        # Añadir un fondo blanco para la etiqueta para mejorar la visibilidad
        ax.text(label_x, label_y, label, ha='center', va='center', 
                color='black', fontweight='bold', fontsize=9,
                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))

# Función para crear campo de fútbol con imagen de fondo
def create_field_plot():
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Intentar cargar la imagen de fondo
    try:
        # Cargar la imagen como fondo
        field_img = mpimg.imread('assets/mediocampo.jpg')
        
        # Configurar los límites del eje para que coincidan con nuestro sistema de coordenadas
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 70)  # Mantener orientación normal
        
        # Mostrar la imagen de fondo
        ax.imshow(field_img, extent=[0, 100, 0, 70], aspect='auto', alpha=1.0)
    except Exception as e:
        # Si no se puede cargar la imagen, usar el fondo verde como respaldo
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 70)
        
        # Dibujar el campo (simplificado para la zona de corner)
        ax.add_patch(plt.Rectangle((0, 0), 100, 70, fill=True, color='green', alpha=0.3))
        ax.add_patch(plt.Rectangle((0, 0), 16.5, 40.3, fill=False, edgecolor='white'))
        ax.add_patch(plt.Rectangle((0, 0), 5.5, 18.3, fill=False, edgecolor='white'))
        circle = plt.Circle((11, 11), 9.15, fill=False, edgecolor='white')
        ax.add_artist(circle)
        
        st.warning("No se pudo cargar la imagen de fondo. Usando campo genérico.")
    
    # Configuraciones comunes
    ax.set_aspect('equal')
    ax.axis('off')
    
    return fig, ax

# Definir el punto de origen del corner basado en el tipo - igual que en registro_corners.py
def get_punto_origen(tipo_corner):
    if tipo_corner == "Derecha":
        return (96, 6)  # Esquina derecha
    else:  # "Izquierda"
        return (4, 6)   # Esquina izquierda

# Definir las zonas de referencia para el punto de caída - igual que en registro_corners.py
def get_zonas_referencia(tipo_corner):
    # Las zonas son: Primer Palo, Centro del Área Pequeña, Segundo Palo,
    # Frontal Palo Cercano, Frontal Centro, Frontal Palo Lejano, 
    # Zona de Rechace, Zona en Corto
    
    if tipo_corner == "Derecha":
        # Corner desde la derecha (viendo hacia la portería)
        return {
            "Primer Palo": (65, 15),         # Primer palo (más alejado del corner)
            "Centro Área Pequeña": (50, 15), # Centro del área pequeña
            "Segundo Palo": (35, 15),        # Segundo palo (más cercano al corner)
            "Frontal Palo Cercano": (35, 30), # Frontal cerca del segundo palo (cercano al lanzamiento)
            "Frontal Centro": (50, 30),      # Frontal centro
            "Frontal Palo Lejano": (65, 30), # Frontal cerca del primer palo (lejano al lanzamiento)
            "Zona de Rechace": (50, 45),     # Zona de rechace
            "Zona en Corto": (80, 20)        # Zona en corto (derecha)
        }
    else:  # "Izquierda"
        # Corner desde la izquierda (viendo hacia la portería)
        return {
            "Primer Palo": (35, 15),         # Primer palo (más alejado del corner)
            "Centro Área Pequeña": (50, 15), # Centro del área pequeña
            "Segundo Palo": (65, 15),        # Segundo palo (más cercano al corner)
            "Frontal Palo Cercano": (65, 30), # Frontal cerca del segundo palo (cercano al lanzamiento)
            "Frontal Centro": (50, 30),      # Frontal centro
            "Frontal Palo Lejano": (35, 30), # Frontal cerca del primer palo (lejano al lanzamiento)
            "Zona de Rechace": (50, 45),     # Zona de rechace
            "Zona en Corto": (20, 20)        # Zona en corto (izquierda)
        }

# Layout de dos filas y dos columnas
# Primera fila: Estadísticas y Posicionamiento Promedio
row1_col1, row1_col2 = st.columns(2)

# Primera fila, primera columna: Estadísticas Generales y Distribución de Zonas
with row1_col1:
    st.subheader("Estadísticas Generales")
    
    # Obtener resultados de corners
    conn = get_db_connection()
    resultados = conn.execute("""
        SELECT resultado, COUNT(*) as cantidad
        FROM corners
        WHERE equipo_id = ?
        GROUP BY resultado
    """, (equipo_id,)).fetchall()
    conn.close()
    
    if resultados:
        # Crear gráfico de resultados
        resultados_df = pd.DataFrame(resultados, columns=['Resultado', 'Cantidad'])
        
        # Mostrar tabla de datos
        st.dataframe(resultados_df)
        
        # Mostrar gráfico
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(resultados_df['Resultado'], resultados_df['Cantidad'])
        ax.set_ylabel('Cantidad')
        ax.set_title('Resultados de Corners')
        plt.xticks(rotation=45, ha='right')
        fig.tight_layout()
        st.pyplot(fig)
        
        # Agregar visualización de distribución de zonas
        st.subheader("Distribución de Zonas de Caída")

        # Verificar si la columna zona_caida existe en la tabla
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(corners)")
        columns = [col[1] for col in cursor.fetchall()]
        has_zona_caida = 'zona_caida' in columns
        conn.close()

        if has_zona_caida:
            try:
                conn = get_db_connection()
                zonas = conn.execute("""
                    SELECT zona_caida, COUNT(*) as cantidad
                    FROM corners
                    WHERE equipo_id = ? 
                    AND zona_caida IS NOT NULL 
                    AND zona_caida != ''
                    GROUP BY zona_caida
                """, (equipo_id,)).fetchall()
                conn.close()
            except Exception as e:
                st.error(f"Error al obtener zonas: {e}")
                zonas = []
            
            if zonas and len(zonas) > 0:
                zonas_df = pd.DataFrame(zonas, columns=['Zona', 'Cantidad'])
                
                # Calcular porcentajes
                total = zonas_df['Cantidad'].sum()
                zonas_df['Porcentaje'] = (zonas_df['Cantidad'] / total * 100).round(1)
                
                # Mostrar tabla de datos
                st.dataframe(zonas_df)
                
                # Mejorar el gráfico de trayectorias
                fig, ax = create_field_plot()
                
                # Definir los puntos de origen de los corners (coordenadas realistas)
                origen_derecha = get_punto_origen("Derecha")
                origen_izquierda = get_punto_origen("Izquierda")
                
                # Contar por tipo de corner y zona
                try:
                    conn = get_db_connection()
                    corner_zonas = conn.execute("""
                        SELECT tipo, zona_caida, COUNT(*) as cantidad
                        FROM corners
                        WHERE equipo_id = ? 
                        AND zona_caida IS NOT NULL 
                        AND zona_caida != ''
                        GROUP BY tipo, zona_caida
                    """, (equipo_id,)).fetchall()
                    conn.close()
                except Exception as e:
                    st.error(f"Error al obtener zonas por tipo: {e}")
                    corner_zonas = []
                
                if corner_zonas:
                    # Crear un DataFrame para facilitar el análisis
                    cz_df = pd.DataFrame(corner_zonas, columns=['Tipo', 'Zona', 'Cantidad'])
                    
                    # Calcular el total para los porcentajes
                    total_corners = cz_df['Cantidad'].sum()
                    
                    # Dibujar las flechas para cada combinación de tipo y zona
                    for _, row in cz_df.iterrows():
                        tipo = row['Tipo']
                        zona = row['Zona']
                        cantidad = row['Cantidad']
                        porcentaje = (cantidad / total_corners * 100).round(1)
                        
                        # Obtener puntos de origen y destino
                        origen = origen_derecha if tipo == 'Derecha' else origen_izquierda
                        
                        # Obtener las coordenadas del destino según la zona
                        # Usamos las mismas zonas de referencia que en el registro
                        zonas_ref = get_zonas_referencia(tipo)
                        if zona in zonas_ref:
                            destino = zonas_ref[zona]
                        else:
                            # Si la zona no está definida, usamos un valor predeterminado
                            destino = (50, 30)
                        
                        # Transformar el eje Y para que sea coherente con la visualización
                        origen_transformado = (origen[0], 70 - origen[1])
                        destino_transformado = (destino[0], 70 - destino[1])
                        
                        # Ajustar la curvatura y grosor según la frecuencia
                        curvature = 0.3  # Aumentada para mejor visualización
                        width = 1 + (porcentaje / 5)  # Grosores más pronunciados
                        
                        create_curved_arrow(
                            ax, 
                            origen_transformado, 
                            destino_transformado, 
                            color='red' if tipo == 'Derecha' else 'blue',  # Colores distintos por tipo
                            width=width,
                            label=f"{porcentaje}%",
                            curvature=curvature
                        )
                    
                    # Añadir leyenda
                    legend_elements = [
                        Line2D([0], [0], color='red', lw=2, label='Corners Derecha'),
                        Line2D([0], [0], color='blue', lw=2, label='Corners Izquierda')
                    ]
                    ax.legend(handles=legend_elements, loc='upper right')
                    
                    # Añadir título y mostrar el gráfico
                    ax.set_title('Distribución de Zonas de Caída de Corners\n(Tamaño de flecha = Frecuencia)')
                    fig.tight_layout()
                    st.pyplot(fig)
                    
                    # Mostrar información adicional
                    st.info("""
                    **Leyenda de zonas:**
                    - **Primer Palo:** Zona cercana al primer poste
                    - **Centro Área Pequeña:** Centro del área pequeña
                    - **Segundo Palo:** Zona cercana al segundo poste
                    - **Frontal:** Zonas más alejadas de la portería
                    - **Rechace:** Zonas donde suelen caer los rechaces
                    - **Corto:** Corners cortos
                    """)
                else:
                    st.info("No hay suficientes datos para mostrar la distribución por tipo y zona.")
            else:
                st.info("No hay datos de zonas de caída registrados.")

# Primera fila, segunda columna: Posicionamiento Promedio Ofensivo
with row1_col2:
    st.subheader("Posicionamiento Promedio Ofensivo")
    
    # Obtener posiciones de jugadores en corners ofensivos
    conn = get_db_connection()
    posiciones = conn.execute("""
        SELECT j.id, j.nombre, j.numero, pj.rol, AVG(pj.x) as x_prom, AVG(pj.y) as y_prom, COUNT(*) as veces
        FROM posiciones_jugadores pj
        JOIN jugadores j ON pj.jugador_id = j.id
        JOIN corners c ON pj.corner_id = c.id
        WHERE pj.equipo_id = ? AND pj.tipo = 'Ofensivo' AND c.equipo_id = ?
        GROUP BY j.id, pj.rol
        ORDER BY veces DESC
    """, (equipo_id, equipo_id)).fetchall()
    conn.close()
    
    if not posiciones:
        st.warning("No hay datos de posicionamiento ofensivo registrados.")
    else:
        # Crear el campo de fútbol para visualizar el posicionamiento promedio
        fig, ax = create_field_plot()
        
        # Dibujar jugadores en sus posiciones promedio
        for pos in posiciones:
            jugador_id, nombre, numero, rol, x_prom, y_prom, veces = pos
            # Transformar la coordenada y para que sea coherente con el registro
            y_transformada = 70 - y_prom  # Invertir el eje Y
            
            color = {'Lanzador': 'purple', 'Rematador': 'orange', 'Bloqueador': 'cyan', 
                    'Arrastre': 'magenta', 'Rechace': 'brown', 'Atrás': 'gray'}.get(rol, 'white')
            
            # Tamaño del círculo proporcional a la frecuencia
            size = 1 + (veces / 5)  # Ajustar según necesidad
            
            circle = plt.Circle((x_prom, y_transformada), size, color=color, alpha=0.7)
            ax.add_artist(circle)
            ax.text(x_prom, y_transformada, str(numero), ha='center', va='center', color='black', fontweight='bold')
        
        # Leyenda
        legend_elements = [
            Line2D([0], [0], marker='o', color='w', markerfacecolor='purple', markersize=10, label='Lanzador'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='orange', markersize=10, label='Rematador'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='cyan', markersize=10, label='Bloqueador'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='magenta', markersize=10, label='Arrastre'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='brown', markersize=10, label='Rechace'),
            Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=10, label='Atrás')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        # Configurar título y mostrar el gráfico
        ax.set_title(f'Posicionamiento Ofensivo Promedio - {equipo_seleccionado}')
        fig.tight_layout()
        st.pyplot(fig)

        # Mostrar distribución de roles en formato de gráfico de barras
        st.subheader("Distribución de Roles")
        roles_df = pd.DataFrame([(p[3], p[6]) for p in posiciones], columns=['Rol', 'Frecuencia'])
        roles_count = roles_df.groupby('Rol').sum().reset_index()
        
        fig, ax = plt.subplots(figsize=(6, 4))
        colors = ['purple', 'orange', 'cyan', 'magenta', 'brown', 'gray']
        sns.barplot(x='Rol', y='Frecuencia', data=roles_count, ax=ax, palette=colors)
        plt.xticks(rotation=45, ha='right')
        ax.set_ylabel('Cantidad')
        ax.set_title('Frecuencia de Roles en Corners')
        plt.tight_layout()
        st.pyplot(fig)

# Sección de visualización de puntos de caída específicos en una fila separada
st.markdown("---")
st.subheader("Puntos de caída registrados")
try:
    conn = get_db_connection()
    # Consulta todos los puntos de caída registrados
    puntos_de_caida = conn.execute("""
        SELECT punto_caida, tipo, resultado, zona_caida
        FROM corners
        WHERE equipo_id = ? 
        AND punto_caida IS NOT NULL 
        AND punto_caida != ''
    """, (equipo_id,)).fetchall()
    conn.close()
    
    if puntos_de_caida and len(puntos_de_caida) > 0:
        fig_puntos, ax_puntos = create_field_plot()
        
        # Contadores para leyenda y análisis
        marcadores = {'Gol': 0, 'Remate': 0, 'Otros': 0}
        zonas_encontradas = set()
        puntos_procesados = 0
        
        for punto in puntos_de_caida:
            try:
                punto_caida, tipo, resultado, zona = punto
                
                # Verificar formato válido
                if not punto_caida or ',' not in punto_caida:
                    continue
                    
                coords = punto_caida.split(',')
                if len(coords) != 2:
                    continue
                
                try:
                    x = float(coords[0])
                    y = float(coords[1])
                except ValueError:
                    continue
                
                # Guardar la zona para análisis
                zona_str = zona if zona else "No especificada"
                zonas_encontradas.add(zona_str)
                
                # Transformar coordenada y
                y_transformada = 70 - y
                
                # Colores según resultado
                if resultado == 'Gol':
                    color = 'green'
                    marker = 'o'
                    marcadores['Gol'] += 1
                elif resultado in ['Remate a puerta', 'Remate fuera']:
                    color = 'red'
                    marker = '^'
                    marcadores['Remate'] += 1
                else:
                    color = 'blue'
                    marker = 's'
                    marcadores['Otros'] += 1
                
                # Dibujar punto
                ax_puntos.scatter(
                    x, y_transformada, 
                    color=color, 
                    marker=marker, 
                    s=100, 
                    alpha=0.7,
                    edgecolors='white'
                )
                
                # Mostrar tipo y zona
                texto = f"{tipo[0]}"
                if zona:
                    texto += f"-{zona[0]}"  # Agregar primera letra de la zona
                    
                ax_puntos.text(
                    x, y_transformada-2, 
                    texto,
                    ha='center', 
                    va='center', 
                    color='white',
                    fontsize=8,
                    bbox=dict(facecolor='black', alpha=0.5, boxstyle='circle,pad=0.1')
                )
                
                puntos_procesados += 1
                
            except Exception as e:
                continue
        
        # Añadir leyenda
        legend_elements = []
        if marcadores['Gol'] > 0:
            legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Gol'))
        if marcadores['Remate'] > 0:
            legend_elements.append(Line2D([0], [0], marker='^', color='w', markerfacecolor='red', markersize=10, label='Remate'))
        if marcadores['Otros'] > 0:
            legend_elements.append(Line2D([0], [0], marker='s', color='w', markerfacecolor='blue', markersize=10, label='Otros'))
        
        if legend_elements:
            ax_puntos.legend(handles=legend_elements, loc='upper right')
        
        ax_puntos.set_title('Puntos de caída registrados\n(Letra indica tipo: D=Derecha, I=Izquierda + Zona)')
        fig_puntos.tight_layout()
        st.pyplot(fig_puntos)
    else:
        st.info("No hay datos de puntos de caída registrados.")
except Exception as e:
    st.error(f"Error al consultar o mostrar puntos de caída: {e}")

# Segunda fila: Datos y Análisis específicos del Jugador
st.markdown("---")
st.header(f"Análisis del Jugador: {jugador_seleccionado if jugadores else ''}")

if not jugadores or jugador_id is None:
    st.warning("No hay jugadores disponibles para analizar.")
else:
    # Obtener datos completos de posicionamiento del jugador
    conn = get_db_connection()
    posiciones_jugador = conn.execute("""
        SELECT c.id, p.fecha, e_rival.nombre as rival, c.minuto, c.tipo, c.resultado, pj.x, pj.y, pj.rol,
               c.zona_caida, c.punto_caida
        FROM posiciones_jugadores pj
        JOIN corners c ON pj.corner_id = c.id
        JOIN partidos p ON c.partido_id = p.id
        JOIN equipos e ON c.equipo_id = e.id
        JOIN equipos e_rival ON (p.equipo_local_id = e_rival.id OR p.equipo_visitante_id = e_rival.id) AND e_rival.id != e.id
        WHERE pj.jugador_id = ? AND pj.tipo = 'Ofensivo'
        ORDER BY p.fecha DESC
    """, (jugador_id,)).fetchall()
    conn.close()
    
    if not posiciones_jugador:
        st.info(f"No hay datos de posicionamiento para {jugador_seleccionado}.")
    else:
        # Convertir los datos a un DataFrame para facilitar análisis
        cols = ['corner_id', 'fecha', 'rival', 'minuto', 'tipo', 'resultado', 'x', 'y', 'rol', 'zona_caida', 'punto_caida']
        df_jugador = pd.DataFrame(posiciones_jugador, columns=cols)
        
        # Crear layout de dos columnas para gráficos del jugador
        col1_jugador, col2_jugador = st.columns(2)
        
        # Columna 1: Mapa de posiciones del jugador
        with col1_jugador:
            st.subheader("Posiciones en el Campo")
            
            # Crear gráfico de posiciones del jugador usando la función con imagen de fondo
            fig, ax = create_field_plot()
            
            # Dibujar todas las posiciones del jugador
            for _, row in df_jugador.iterrows():
                # Transformar la coordenada y
                y_transformada = 70 - row['y']  # Invertir el eje Y
                
                # Colores según resultado
                if row['resultado'] == 'Gol':
                    color = 'green'
                    marker = 'o'
                elif row['resultado'] in ['Remate a puerta', 'Remate fuera']:
                    color = 'red'
                    marker = '^'
                else:
                    color = 'blue'
                    marker = 's'
                
                ax.scatter(row['x'], y_transformada, color=color, marker=marker, s=100, alpha=0.7)
                
                # Añadir número de minuto al lado de cada punto
                ax.text(row['x']+1, y_transformada, f"{row['minuto']}", fontsize=8)
            
            # Leyenda
            legend_elements = [
                Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Gol'),
                Line2D([0], [0], marker='^', color='w', markerfacecolor='red', markersize=10, label='Remate'),
                Line2D([0], [0], marker='s', color='w', markerfacecolor='blue', markersize=10, label='Otros')
            ]
            ax.legend(handles=legend_elements, loc='upper right')
            
            # Configurar título y mostrar el gráfico
            ax.set_title(f'Posiciones de {jugador_seleccionado} en Corners')
            fig.tight_layout()
            st.pyplot(fig)
            
            # Datos adicionales
            st.markdown(f"**Total de corners jugados:** {len(df_jugador)}")
            
            # Estadísticas de éxito
            goles = df_jugador[df_jugador['resultado'] == 'Gol'].shape[0]
            remates = df_jugador[df_jugador['resultado'].isin(['Remate a puerta', 'Remate fuera'])].shape[0]
            
            st.markdown(f"**Goles:** {goles} ({(goles/len(df_jugador)*100):.1f}%)")
            st.markdown(f"**Remates:** {remates} ({(remates/len(df_jugador)*100):.1f}%)")
        
        # Columna 2: Gráfico de distribución de roles y resultados
        with col2_jugador:
            st.subheader("Distribución de Roles")
            
            # Contar frecuencia de roles
            roles_count = df_jugador['rol'].value_counts().reset_index()
            roles_count.columns = ['Rol', 'Cantidad']
            
            # Crear gráfico de roles
            fig, ax = plt.subplots(figsize=(8, 5))
            
            # Definir colores para roles específicos
            colores_roles = {
                'Lanzador': 'purple',
                'Rematador': 'orange',
                'Bloqueador': 'cyan',
                'Arrastre': 'magenta',
                'Rechace': 'brown',
                'Atrás': 'gray'
            }
            
            # Extraer colores en el orden de los roles del dataframe
            colores = [colores_roles.get(rol, 'lightgray') for rol in roles_count['Rol']]
            
            # Crear gráfico de barras
            ax.bar(roles_count['Rol'], roles_count['Cantidad'], color=colores)
            ax.set_ylabel('Cantidad')
            ax.set_title(f'Roles de {jugador_seleccionado.split(" - ")[1]} en Corners')
            plt.xticks(rotation=45, ha='right')
            fig.tight_layout()
            st.pyplot(fig)
            
            # Gráfico de distribución de resultados
            st.subheader("Resultados por Participación")
            
            # Contar frecuencia de resultados
            resultados_count = df_jugador['resultado'].value_counts().reset_index()
            resultados_count.columns = ['Resultado', 'Cantidad']
            
            fig, ax = plt.subplots(figsize=(8, 5))
            # Definir colores para resultados
            colores_resultados = {
                'Gol': 'green',
                'Remate a puerta': 'orange',
                'Remate fuera': 'red',
                'Despeje': 'gray',
                'Falta atacante': 'brown',
                'Falta defensiva': 'blue',
                'Otro': 'lightgray'
            }
            
            # Extraer colores en el orden de los resultados del dataframe
            colores = [colores_resultados.get(res, 'lightgray') for res in resultados_count['Resultado']]
            
            # Crear gráfico de barras
            ax.bar(resultados_count['Resultado'], resultados_count['Cantidad'], color=colores)
            ax.set_ylabel('Cantidad')
            ax.set_title(f'Resultados con {jugador_seleccionado.split(" - ")[1]} en el Campo')
            plt.xticks(rotation=45, ha='right')
            fig.tight_layout()
            st.pyplot(fig)
        
        # Gráfico de mapa de calor para zonas frecuentes
        if df_jugador.shape[0] >= 3:  # Solo si hay suficientes datos
            st.subheader("Mapa de Calor de Posicionamiento")
            
            # Crear nueva figura
            fig, ax = plt.subplots(figsize=(10, 7))
            
            # Intentar cargar la imagen de fondo
            try:
                field_img = mpimg.imread('assets/mediocampo.jpg')
                ax.imshow(field_img, extent=[0, 100, 0, 70], aspect='auto', alpha=0.6)
            except:
                # Si falla, usar un fondo verde simple
                ax.set_facecolor('#78A64B')  # Verde césped
                
            # Preparar los datos para el mapa de calor
            x = df_jugador['x'].values
            y = 70 - df_jugador['y'].values  # Invertir Y para coherencia
            
            # Generar un mapa de calor 2D usando kernel density estimation
            if len(x) > 1:
                sns.kdeplot(
                    x=x, 
                    y=y, 
                    cmap="hot",
                    fill=True,
                    alpha=0.7,
                    thresh=0,
                    levels=10,
                    ax=ax
                )
            
            # Configuraciones adicionales
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 70)
            ax.set_title(f"Mapa de Calor: Zonas Frecuentes de {jugador_seleccionado.split(' - ')[1]}")
            ax.axis('off')
            fig.tight_layout()
            st.pyplot(fig)
            
            # Columnas para análisis adicionales
            col3_jugador, col4_jugador = st.columns(2)
            
            # En la columna 3: Análisis de efectividad contra rivales
            with col3_jugador:
                st.subheader("Efectividad contra Rivales")
                
                if len(df_jugador['rival'].unique()) > 1:
                    # Agrupar por rival y resultado
                    rival_results = df_jugador.groupby(['rival', 'resultado']).size().unstack(fill_value=0)
                    
                    # Calcular totales
                    rival_results['Total'] = rival_results.sum(axis=1)
                    
                    # Calcular porcentaje de éxito (goles + remates)
                    if 'Gol' in rival_results.columns:
                        rival_results['Goles %'] = (rival_results['Gol'] / rival_results['Total'] * 100).round(1)
                    else:
                        rival_results['Goles %'] = 0
                        
                    # Crear columna para remates combinados si existen
                    remates_cols = [col for col in rival_results.columns if 'Remate' in col]
                    if remates_cols:
                        rival_results['Remates'] = rival_results[remates_cols].sum(axis=1)
                        rival_results['Remates %'] = (rival_results['Remates'] / rival_results['Total'] * 100).round(1)
                    
                    # Mostrar tabla de efectividad
                    st.dataframe(rival_results)
                    
                    # Visualizar efectividad por rival
                    fig, ax = plt.subplots(figsize=(8, 5))
                    
                    # Preparar datos para gráfico
                    rivales = rival_results.index
                    goles_pct = rival_results['Goles %'] if 'Goles %' in rival_results.columns else [0] * len(rivales)
                    remates_pct = rival_results['Remates %'] if 'Remates %' in rival_results.columns else [0] * len(rivales)
                    
                    # Crear barras
                    x = np.arange(len(rivales))
                    width = 0.35
                    
                    ax.bar(x - width/2, goles_pct, width, label='% Goles', color='green')
                    ax.bar(x + width/2, remates_pct, width, label='% Remates', color='orange')
                    
                    # Configurar eje X
                    ax.set_xticks(x)
                    ax.set_xticklabels(rivales, rotation=45, ha='right')
                    
                    # Añadir etiquetas y título
                    ax.set_ylabel('Porcentaje %')
                    ax.set_title(f'Efectividad contra Rivales')
                    ax.legend()
                    
                    fig.tight_layout()
                    st.pyplot(fig)
                else:
                    st.info("No hay suficientes rivales para mostrar comparativa.")
            
            # En la columna 4: Análisis de tendencias y combinaciones
            with col4_jugador:
                st.subheader("Tendencias de Rendimiento")
                
                # Ordenar los datos por fecha
                df_chronological = df_jugador.sort_values('fecha')
                
                # Crear columna de resultado numérico para visualizar tendencia
                result_value = {
                    'Gol': 3,            # Valor más alto para goles
                    'Remate a puerta': 2, # Valor medio para remates a puerta
                    'Remate fuera': 1,   # Valor bajo para remates fuera
                    'Despeje': 0,        # Valores neutros o negativos para otros resultados
                    'Falta atacante': -1,
                    'Falta defensiva': -1,
                    'Otro': 0
                }
                
                # Aplicar mapeo y crear columna numérica
                df_chronological['valor_resultado'] = df_chronological['resultado'].map(
                    lambda x: result_value.get(x, 0)
                )
                
                # Crear índice ordenado para el eje X
                df_chronological['indice'] = range(len(df_chronological))
                
                if len(df_chronological) > 1:
                    # Graficar tendencia de rendimiento
                    fig, ax = plt.subplots(figsize=(8, 5))
                    
                    # Graficar línea de tendencia
                    ax.plot(df_chronological['indice'], df_chronological['valor_resultado'], 
                            'o-', color='blue', alpha=0.7, label='Rendimiento')
                    
                    # Añadir línea de tendencia (media móvil) si hay suficientes datos
                    if len(df_chronological) > 2:
                        window = min(3, len(df_chronological))
                        df_chronological['tendencia'] = df_chronological['valor_resultado'].rolling(window=window, center=True).mean()
                        ax.plot(df_chronological['indice'], df_chronological['tendencia'], 
                                '-', color='red', linewidth=2, label=f'Tendencia (media móvil {window})')
                    
                    # Configurar etiquetas del eje X
                    xticks = df_chronological['indice']
                    xticklabels = [f"{r['fecha']}" for _, r in df_chronological.iterrows()]
                    
                    if len(xticks) > 8:  # Si hay muchas fechas, mostrar solo algunas
                        step = len(xticks) // 6
                        xticks = xticks[::step]
                        xticklabels = xticklabels[::step]
                    
                    ax.set_xticks(xticks)
                    ax.set_xticklabels(xticklabels, rotation=45, ha='right')
                    
                    # Añadir línea horizontal en 0
                    ax.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
                    
                    # Configurar límites y etiquetas
                    ax.set_ylim(-1.5, 3.5)
                    ax.set_ylabel('Rendimiento')
                    ax.set_title(f'Evolución del Rendimiento')
                    ax.legend()
                    
                    fig.tight_layout()
                    st.pyplot(fig)
                else:
                    st.info("Se necesitan más participaciones para analizar tendencias.")
                
                # Análisis de combinaciones con otros jugadores
                st.subheader("Combinaciones Efectivas")
                
                # Obtener datos de combinaciones con otros jugadores
                conn = get_db_connection()
                combinaciones = conn.execute("""
                    SELECT j.nombre, j.numero, c.resultado, COUNT(*) as veces
                    FROM posiciones_jugadores pj1
                    JOIN corners c ON pj1.corner_id = c.id
                    JOIN posiciones_jugadores pj2 ON pj1.corner_id = pj2.corner_id AND pj1.jugador_id != pj2.jugador_id
                    JOIN jugadores j ON pj2.jugador_id = j.id
                    WHERE pj1.jugador_id = ? AND pj1.tipo = 'Ofensivo' AND pj2.tipo = 'Ofensivo'
                    GROUP BY j.id, c.resultado
                    ORDER BY veces DESC
                """, (jugador_id,)).fetchall()
                conn.close()
                
                if combinaciones:
                    # Crear DataFrame
                    df_comb = pd.DataFrame(combinaciones, columns=['Jugador', 'Número', 'Resultado', 'Veces'])
                    
                    # Pivotear para obtener tabla de eficacia
                    if len(df_comb) > 0:
                        pivot_comb = df_comb.pivot_table(
                            index=['Jugador', 'Número'],
                            columns='Resultado',
                            values='Veces',
                            aggfunc='sum',
                            fill_value=0
                        ).reset_index()
                        
                        # Calcular totales
                        pivot_comb['Total'] = pivot_comb.drop(['Jugador', 'Número'], axis=1).sum(axis=1)
                        
                        # Ordenar por total
                        pivot_comb = pivot_comb.sort_values('Total', ascending=False)
                        
                        # Mostrar tabla de las 5 mejores combinaciones
                        st.dataframe(pivot_comb.head(5))
                    else:
                        st.info("No hay datos suficientes sobre combinaciones con otros jugadores.")
                else:
                    st.info("No hay datos suficientes sobre combinaciones con otros jugadores.")
                
        # Tabla detallada de participación
        st.subheader("Detalles de Participación")
        
        # Crear una versión formateada del DataFrame para mostrar
        df_display = df_jugador[['fecha', 'rival', 'minuto', 'tipo', 'resultado', 'rol', 'zona_caida']]
        df_display.columns = ['Fecha', 'Rival', 'Minuto', 'Tipo Corner', 'Resultado', 'Rol', 'Zona de Caída']
        
        # Mostrar los datos en una tabla interactiva
        st.dataframe(df_display)