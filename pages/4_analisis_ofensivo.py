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
           p.equipo_local_id, p.equipo_visitante_id
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

# Layout de dos filas y dos columnas
# Primera fila: Estadísticas y Posicionamiento Promedio
row1_col1, row1_col2 = st.columns(2)

# Primera fila, primera columna: Estadísticas Generales
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
        # Modificar la sección de "Distribución de Zonas de Caída" en row1_col1 con este código:

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
                origen_derecha = (100, 0)    # Esquina derecha (ajustado)
                origen_izquierda = (0, 0)    # Esquina izquierda (ajustado)
                
                # Definir mejor los puntos destino de las zonas (coordenadas más realistas)
                destinos = {
                    "Primer Palo": (85, 15),
                    "Centro Área Pequeña": (70, 15),
                    "Segundo Palo": (55, 15),
                    "Frontal Palo Cercano": (85, 30),
                    "Frontal Centro": (70, 30),
                    "Frontal Palo Lejano": (55, 30),
                    "Zona de Rechace": (70, 45),
                    "Zona en Corto": (90, 20) if equipo_id == equipo_local_id else (10, 20),
                    "Personalizada": (70, 25)  # Valor predeterminado para zonas personalizadas
                }
                
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
                        
                        origen = origen_derecha if tipo == 'Derecha' else origen_izquierda
                        destino = destinos.get(zona, (70, 25))  # Usar el destino correspondiente o un valor predeterminado
                        
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
                    from matplotlib.lines import Line2D
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
                
            # Mejorar la visualización de puntos personalizados
            try:
                conn = get_db_connection()
                puntos_personalizados = conn.execute("""
                    SELECT punto_caida, tipo, resultado
                    FROM corners
                    WHERE equipo_id = ? 
                    AND punto_caida IS NOT NULL 
                    AND punto_caida != ''
                    AND zona_caida = 'Personalizada'
                """, (equipo_id,)).fetchall()
                conn.close()
                
                if puntos_personalizados and len(puntos_personalizados) > 0:
                    st.subheader("Puntos de caída personalizados")
                    fig_personal, ax_personal = create_field_plot()
                    
                    # Contadores para leyenda
                    marcadores = {'Gol': 0, 'Remate': 0, 'Otros': 0}
                    
                    for punto in puntos_personalizados:
                        try:
                            coords = punto[0].split(',')
                            x = float(coords[0])
                            y = float(coords[1])
                            tipo = punto[1]
                            resultado = punto[2]
                            
                            # Transformar la coordenada y
                            y_transformada = 70 - y
                            
                            # Determinar color y marcador según resultado
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
                            ax_personal.scatter(
                                x, y_transformada, 
                                color=color, 
                                marker=marker, 
                                s=100, 
                                alpha=0.7,
                                edgecolors='white'
                            )
                            
                            # Añadir pequeño indicador del tipo de corner
                            ax_personal.text(
                                x, y_transformada-2, 
                                tipo[0],  # Primera letra del tipo (D/I)
                                ha='center', 
                                va='center', 
                                color='white',
                                fontsize=8,
                                bbox=dict(facecolor='black', alpha=0.5, boxstyle='circle,pad=0.1')
                            )
                        except Exception as e:
                            continue  # Ignorar puntos mal formateados
                    
                    # Añadir leyenda solo para los marcadores usados
                    legend_elements = []
                    if marcadores['Gol'] > 0:
                        legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10, label='Gol'))
                    if marcadores['Remate'] > 0:
                        legend_elements.append(Line2D([0], [0], marker='^', color='w', markerfacecolor='red', markersize=10, label='Remate'))
                    if marcadores['Otros'] > 0:
                        legend_elements.append(Line2D([0], [0], marker='s', color='w', markerfacecolor='blue', markersize=10, label='Otros'))
                    
                    if legend_elements:
                        ax_personal.legend(handles=legend_elements, loc='upper right')
                    
                    ax_personal.set_title('Puntos de caída personalizados\n(Letra indica tipo: D=Derecha, I=Izquierda)')
                    fig_personal.tight_layout()
                    st.pyplot(fig_personal)
            except Exception as e:
                st.warning(f"No se pudieron cargar los puntos personalizados: {e}")
        else:
            st.info("La función de análisis de zonas de caída estará disponible después de registrar corners con información de trayectoria.")

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
        from matplotlib.lines import Line2D
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

# Segunda fila
st.markdown("---")

# Segunda fila, primera columna: Datos de Posicionamiento
row2_col1, row2_col2 = st.columns(2)

with row2_col1:
    st.subheader("Datos de Posicionamiento")
    if not posiciones:
        st.warning("No hay datos de posicionamiento registrados.")
    else:
        posiciones_df = pd.DataFrame(posiciones, columns=['ID', 'Nombre', 'Número', 'Rol', 'X Promedio', 'Y Promedio', 'Frecuencia'])
        st.dataframe(posiciones_df[['Nombre', 'Número', 'Rol', 'X Promedio', 'Y Promedio', 'Frecuencia']])

# Segunda fila, segunda columna: Análisis por Jugador
with row2_col2:
    st.subheader(f"Análisis del Jugador: {jugador_seleccionado if jugadores else ''}")
    
    if not jugadores or jugador_id is None:
        st.warning("No hay jugadores disponibles para analizar.")
    else:
        # Obtener datos de posicionamiento del jugador
        conn = get_db_connection()
        posiciones_jugador = conn.execute("""
            SELECT c.id, p.fecha, e_rival.nombre as rival, c.minuto, c.tipo, c.resultado, pj.x, pj.y, pj.rol
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
            # Crear gráfico de posiciones del jugador usando la función con imagen de fondo
            fig, ax = create_field_plot()
            
            # Dibujar todas las posiciones del jugador
            for pos in posiciones_jugador:
                corner_id, fecha, rival, minuto, tipo, resultado, x, y, rol = pos
                # Transformar la coordenada y
                y_transformada = 70 - y  # Invertir el eje Y
                
                color = 'green' if resultado == 'Gol' else 'red' if resultado in ['Remate a puerta', 'Remate fuera'] else 'blue'
                marker = 'o' if resultado == 'Gol' else '^' if resultado in ['Remate a puerta', 'Remate fuera'] else 's'
                
                ax.scatter(x, y_transformada, color=color, marker=marker, s=100, alpha=0.7)
            
            # Leyenda
            from matplotlib.lines import Line2D
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

# Tabla de datos del jugador seleccionado
if jugadores and jugador_id is not None and posiciones_jugador:
    st.markdown("---")
    st.subheader("Corners con participación del jugador:")
    posiciones_df = pd.DataFrame(posiciones_jugador, 
                               columns=['ID', 'Fecha', 'Rival', 'Minuto', 'Tipo', 'Resultado', 'X', 'Y', 'Rol'])
    st.dataframe(posiciones_df[['Fecha', 'Rival', 'Minuto', 'Tipo', 'Resultado', 'Rol']])