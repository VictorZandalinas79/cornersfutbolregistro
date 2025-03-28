import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from utils.db import get_db_connection
import os
from PIL import Image
import matplotlib.image as mpimg

# Verificar si el usuario está logueado
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.warning("Por favor, inicia sesión primero.")
    st.stop()

st.title("Análisis de Posicionamiento Ofensivo")

# Obtener lista de equipos
conn = get_db_connection()
equipos = conn.execute("SELECT id, nombre FROM equipos").fetchall()
conn.close()

if not equipos:
    st.warning("No hay equipos registrados.")
    st.stop()

# Selector de equipo
equipo_opciones = {equipo[1]: equipo[0] for equipo in equipos}
equipo_seleccionado = st.selectbox("Selecciona un Equipo", list(equipo_opciones.keys()))
equipo_id = equipo_opciones[equipo_seleccionado]

# Obtener corners ofensivos del equipo
conn = get_db_connection()
corners = conn.execute("""
    SELECT c.id, p.fecha, e1.nombre as local, e2.nombre as visitante, c.minuto, c.tipo, c.resultado
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

st.info(f"Se encontraron {len(corners)} corners ofensivos para {equipo_seleccionado}")

# Mostrar estadísticas generales
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
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        st.write("Resultados de corners:")
        st.dataframe(resultados_df)
    
    with col2:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(resultados_df['Resultado'], resultados_df['Cantidad'])
        ax.set_ylabel('Cantidad')
        ax.set_title('Resultados de Corners')
        plt.xticks(rotation=45, ha='right')
        fig.tight_layout()
        st.pyplot(fig)

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

# Posicionamiento promedio ofensivo
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
    
    # Mostrar tabla con datos
    st.subheader("Datos de Posicionamiento")
    posiciones_df = pd.DataFrame(posiciones, columns=['ID', 'Nombre', 'Número', 'Rol', 'X Promedio', 'Y Promedio', 'Frecuencia'])
    st.dataframe(posiciones_df[['Nombre', 'Número', 'Rol', 'X Promedio', 'Y Promedio', 'Frecuencia']])

# Análisis por jugador
st.subheader("Análisis por Jugador")

# Obtener lista de jugadores del equipo
conn = get_db_connection()
jugadores = conn.execute("""
    SELECT id, nombre, numero 
    FROM jugadores 
    WHERE equipo_id = ?
    ORDER BY numero
""", (equipo_id,)).fetchall()
conn.close()

if not jugadores:
    st.warning(f"No hay jugadores registrados para {equipo_seleccionado}.")
else:
    # Selector de jugador
    jugador_opciones = {f"{j[2]} - {j[1]}": j[0] for j in jugadores}
    jugador_seleccionado = st.selectbox("Selecciona un Jugador", list(jugador_opciones.keys()))
    jugador_id = jugador_opciones[jugador_seleccionado]
    
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
        st.info(f"No hay datos de posicionamiento para el jugador seleccionado.")
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
        ax.set_title(f'Posiciones de {jugador_seleccionado} en Corners Ofensivos')
        fig.tight_layout()
        st.pyplot(fig)
        
        # Mostrar tabla con datos
        st.write("Corners con participación del jugador:")
        posiciones_df = pd.DataFrame(posiciones_jugador, 
                                    columns=['ID', 'Fecha', 'Rival', 'Minuto', 'Tipo', 'Resultado', 'X', 'Y', 'Rol'])
        st.dataframe(posiciones_df[['Fecha', 'Rival', 'Minuto', 'Tipo', 'Resultado', 'Rol']])