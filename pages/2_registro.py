import streamlit as st
import sqlite3
from utils.db import get_db_connection

# Verificar si el usuario está logueado
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.warning("Por favor, inicia sesión primero.")
    st.stop()

st.title("Registro de Equipos, Jugadores y Partidos")

# Crear pestañas para las diferentes secciones
tab_equipos, tab_jugadores, tab_partidos = st.tabs(["Equipos", "Jugadores", "Partidos"])

# Sección de Equipos
with tab_equipos:
    st.header("Registro de Equipos")
    
    # Formulario para agregar un nuevo equipo
    with st.form("nuevo_equipo"):
        nombre_equipo = st.text_input("Nombre del Equipo")
        submit_equipo = st.form_submit_button("Registrar Equipo")
        
        if submit_equipo and nombre_equipo:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO equipos (nombre) VALUES (?)", (nombre_equipo,))
                conn.commit()
                st.success(f"Equipo '{nombre_equipo}' registrado correctamente")
            except sqlite3.IntegrityError:
                st.error(f"El equipo '{nombre_equipo}' ya existe")
            finally:
                conn.close()
    
    # Mostrar equipos registrados con opciones de editar y eliminar
    st.subheader("Equipos Registrados")
    conn = get_db_connection()
    equipos = conn.execute("SELECT id, nombre FROM equipos").fetchall()
    conn.close()
    
    if equipos:
        # Seleccionar equipo para editar o eliminar
        equipo_opciones = {f"{equipo[1]}": equipo[0] for equipo in equipos}
        equipo_seleccionado_editar = st.selectbox("Seleccionar equipo para editar/eliminar", 
                                            list(equipo_opciones.keys()),
                                            key="equipo_editar")
        equipo_id_editar = equipo_opciones[equipo_seleccionado_editar]
        
        # Mostrar opciones de editar o eliminar
        col1, col2 = st.columns(2)
        
        # Editar equipo
        with col1:
            with st.expander("Editar Equipo"):
                with st.form("editar_equipo"):
                    nuevo_nombre = st.text_input("Nuevo nombre del equipo", value=equipo_seleccionado_editar)
                    submit_editar = st.form_submit_button("Actualizar")
                    
                    if submit_editar:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            cursor.execute("UPDATE equipos SET nombre = ? WHERE id = ?", 
                                       (nuevo_nombre, equipo_id_editar))
                            conn.commit()
                            if cursor.rowcount > 0:
                                st.success("Equipo actualizado correctamente")
                                st.rerun()
                            else:
                                st.warning("No se realizaron cambios")
                        except sqlite3.IntegrityError:
                            st.error("Error al actualizar el equipo. El nombre ya existe.")
                        finally:
                            conn.close()
        
        # Eliminar equipo
        with col2:
            with st.expander("Eliminar Equipo"):
                st.warning(f"Al eliminar el equipo '{equipo_seleccionado_editar}' se eliminarán también sus jugadores y partidos relacionados.")
                
                # Verificar si el equipo tiene jugadores
                conn = get_db_connection()
                tiene_jugadores = conn.execute("SELECT COUNT(*) FROM jugadores WHERE equipo_id = ?", 
                                           (equipo_id_editar,)).fetchone()[0]
                
                # Verificar si el equipo tiene partidos
                tiene_partidos = conn.execute("""
                    SELECT COUNT(*) FROM partidos 
                    WHERE equipo_local_id = ? OR equipo_visitante_id = ?
                """, (equipo_id_editar, equipo_id_editar)).fetchone()[0]
                conn.close()
                
                if tiene_jugadores > 0:
                    st.info(f"Este equipo tiene {tiene_jugadores} jugadores registrados.")
                
                if tiene_partidos > 0:
                    st.info(f"Este equipo tiene {tiene_partidos} partidos registrados.")
                
                confirmation = st.text_input("Escribe 'ELIMINAR' para confirmar", key="confirm_delete_equipo")
                
                if st.button("Eliminar Equipo"):
                    if confirmation == "ELIMINAR":
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            # Iniciar transacción
                            cursor.execute("BEGIN TRANSACTION")
                            
                            # Eliminar posiciones de jugadores
                            cursor.execute("""
                                DELETE FROM posiciones_jugadores 
                                WHERE jugador_id IN (SELECT id FROM jugadores WHERE equipo_id = ?)
                            """, (equipo_id_editar,))
                            
                            # Eliminar corners de partidos del equipo
                            cursor.execute("""
                                DELETE FROM corners 
                                WHERE partido_id IN (
                                    SELECT id FROM partidos 
                                    WHERE equipo_local_id = ? OR equipo_visitante_id = ?
                                )
                            """, (equipo_id_editar, equipo_id_editar))
                            
                            # Eliminar jugadores del equipo
                            cursor.execute("DELETE FROM jugadores WHERE equipo_id = ?", 
                                       (equipo_id_editar,))
                            
                            # Eliminar partidos del equipo
                            cursor.execute("""
                                DELETE FROM partidos 
                                WHERE equipo_local_id = ? OR equipo_visitante_id = ?
                            """, (equipo_id_editar, equipo_id_editar))
                            
                            # Finalmente eliminar el equipo
                            cursor.execute("DELETE FROM equipos WHERE id = ?", (equipo_id_editar,))
                            
                            conn.commit()
                            st.success("Equipo eliminado correctamente")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Error al eliminar el equipo: {e}")
                        finally:
                            conn.close()
                    else:
                        st.error("Confirmación incorrecta. El equipo no ha sido eliminado.")
        
        # Mostrar lista de equipos
        st.subheader("Lista de Equipos")
        for equipo in equipos:
            st.write(f"ID: {equipo[0]} - {equipo[1]}")
    else:
        st.info("No hay equipos registrados")

# Sección de Jugadores
with tab_jugadores:
    st.header("Registro de Jugadores")
    
    # Obtener lista de equipos para el selector
    conn = get_db_connection()
    equipos = conn.execute("SELECT id, nombre FROM equipos").fetchall()
    conn.close()
    
    if not equipos:
        st.warning("Primero debes registrar equipos")
    else:
        # Selector de equipo
        equipo_opciones = {equipo[1]: equipo[0] for equipo in equipos}
        equipo_seleccionado = st.selectbox("Selecciona un Equipo", list(equipo_opciones.keys()), key="equipo_jugadores")
        equipo_id = equipo_opciones[equipo_seleccionado]
        
        # Formulario para agregar un nuevo jugador
        with st.form("nuevo_jugador"):
            nombre_jugador = st.text_input("Nombre del Jugador")
            numero_jugador = st.number_input("Número", min_value=1, max_value=99, step=1)
            submit_jugador = st.form_submit_button("Registrar Jugador")
            
            if submit_jugador and nombre_jugador:
                conn = get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("INSERT INTO jugadores (nombre, equipo_id, numero) VALUES (?, ?, ?)", 
                                 (nombre_jugador, equipo_id, numero_jugador))
                    conn.commit()
                    st.success(f"Jugador '{nombre_jugador}' registrado correctamente")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Error al registrar el jugador")
                finally:
                    conn.close()
        
        # Mostrar jugadores registrados para el equipo seleccionado
        st.subheader(f"Jugadores de {equipo_seleccionado}")
        conn = get_db_connection()
        jugadores = conn.execute("SELECT id, nombre, numero FROM jugadores WHERE equipo_id = ? ORDER BY numero", 
                               (equipo_id,)).fetchall()
        conn.close()
        
        if jugadores:
            # Opciones para editar o eliminar jugador
            jugador_opciones = {f"#{j[2]} {j[1]}": j[0] for j in jugadores}
            jugador_seleccionado_editar = st.selectbox("Seleccionar jugador para editar/eliminar", 
                                                  list(jugador_opciones.keys()),
                                                  key="jugador_editar")
            jugador_id_editar = jugador_opciones[jugador_seleccionado_editar]
            
            # Obtener datos actuales del jugador
            conn = get_db_connection()
            jugador_actual = conn.execute("SELECT nombre, numero FROM jugadores WHERE id = ?", 
                                       (jugador_id_editar,)).fetchone()
            conn.close()
            
            if jugador_actual:
                nombre_actual, numero_actual = jugador_actual
                
                col1, col2 = st.columns(2)
                
                # Editar jugador
                with col1:
                    with st.expander("Editar Jugador"):
                        with st.form("editar_jugador"):
                            nuevo_nombre = st.text_input("Nuevo nombre del jugador", value=nombre_actual)
                            nuevo_numero = st.number_input("Nuevo número", min_value=1, max_value=99, value=numero_actual)
                            submit_editar_jugador = st.form_submit_button("Actualizar")
                            
                            if submit_editar_jugador:
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                try:
                                    cursor.execute("""
                                        UPDATE jugadores 
                                        SET nombre = ?, numero = ? 
                                        WHERE id = ?
                                    """, (nuevo_nombre, nuevo_numero, jugador_id_editar))
                                    conn.commit()
                                    st.success("Jugador actualizado correctamente")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al actualizar el jugador: {e}")
                                finally:
                                    conn.close()
                
                # Eliminar jugador
                with col2:
                    with st.expander("Eliminar Jugador"):
                        st.warning("Esta acción no se puede deshacer.")
                        
                        # Verificar si el jugador tiene posiciones registradas
                        conn = get_db_connection()
                        tiene_posiciones = conn.execute("""
                            SELECT COUNT(*) FROM posiciones_jugadores WHERE jugador_id = ?
                        """, (jugador_id_editar,)).fetchone()[0]
                        conn.close()
                        
                        if tiene_posiciones > 0:
                            st.info(f"Este jugador tiene {tiene_posiciones} posiciones registradas en corners.")
                        
                        if st.button("Eliminar Jugador"):
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            try:
                                # Iniciar transacción
                                cursor.execute("BEGIN TRANSACTION")
                                
                                # Eliminar posiciones del jugador
                                cursor.execute("DELETE FROM posiciones_jugadores WHERE jugador_id = ?", 
                                           (jugador_id_editar,))
                                
                                # Eliminar jugador
                                cursor.execute("DELETE FROM jugadores WHERE id = ?", (jugador_id_editar,))
                                
                                conn.commit()
                                st.success("Jugador eliminado correctamente")
                                st.rerun()
                            except Exception as e:
                                conn.rollback()
                                st.error(f"Error al eliminar el jugador: {e}")
                            finally:
                                conn.close()
            
            # Mostrar lista de jugadores
            st.subheader("Lista de Jugadores")
            for jugador in jugadores:
                st.write(f"ID: {jugador[0]} - #{jugador[2]} {jugador[1]}")
        else:
            st.info(f"No hay jugadores registrados para {equipo_seleccionado}")

# Sección de Partidos
with tab_partidos:
    st.header("Registro de Partidos")
    
    # Obtener lista de equipos para los selectores
    conn = get_db_connection()
    equipos = conn.execute("SELECT id, nombre FROM equipos").fetchall()
    conn.close()
    
    if len(equipos) < 2:
        st.warning("Necesitas al menos dos equipos para registrar un partido")
    else:
        # Selectores de equipos
        equipo_opciones = {equipo[1]: equipo[0] for equipo in equipos}
        equipo_local = st.selectbox("Equipo Local", list(equipo_opciones.keys()), key="local")
        equipo_visitante = st.selectbox("Equipo Visitante", list(equipo_opciones.keys()), key="visitante")
        
        if equipo_local == equipo_visitante:
            st.error("El equipo local y visitante deben ser diferentes")
        else:
            # Formulario para registrar un nuevo partido
            with st.form("nuevo_partido"):
                fecha_partido = st.date_input("Fecha del Partido")
                submit_partido = st.form_submit_button("Registrar Partido")
                
                if submit_partido:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO partidos (equipo_local_id, equipo_visitante_id, fecha) VALUES (?, ?, ?)", 
                            (equipo_opciones[equipo_local], equipo_opciones[equipo_visitante], fecha_partido)
                        )
                        conn.commit()
                        st.success(f"Partido {equipo_local} vs {equipo_visitante} registrado correctamente")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar el partido: {e}")
                    finally:
                        conn.close()
            
            # Mostrar partidos registrados
            st.subheader("Partidos Registrados")
            conn = get_db_connection()
            partidos = conn.execute("""
                SELECT p.id, e1.nombre, e2.nombre, p.fecha 
                FROM partidos p
                JOIN equipos e1 ON p.equipo_local_id = e1.id
                JOIN equipos e2 ON p.equipo_visitante_id = e2.id
                ORDER BY p.fecha DESC
            """).fetchall()
            conn.close()
            
            if partidos:
                # Opciones para eliminar partido
                partido_opciones = {f"{p[1]} vs {p[2]} ({p[3]})": p[0] for p in partidos}
                partido_seleccionado_eliminar = st.selectbox("Seleccionar partido para eliminar", 
                                                        list(partido_opciones.keys()),
                                                        key="partido_eliminar")
                partido_id_eliminar = partido_opciones[partido_seleccionado_eliminar]
                
                with st.expander("Eliminar Partido"):
                    st.warning("Esta acción eliminará el partido y todos sus corners asociados.")
                    
                    # Verificar si el partido tiene corners registrados
                    conn = get_db_connection()
                    tiene_corners = conn.execute("""
                        SELECT COUNT(*) FROM corners WHERE partido_id = ?
                    """, (partido_id_eliminar,)).fetchone()[0]
                    conn.close()
                    
                    if tiene_corners > 0:
                        st.info(f"Este partido tiene {tiene_corners} corners registrados.")
                    
                    if st.button("Eliminar Partido"):
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            # Iniciar transacción
                            cursor.execute("BEGIN TRANSACTION")
                            
                            # Eliminar posiciones de jugadores en corners del partido
                            cursor.execute("""
                                DELETE FROM posiciones_jugadores 
                                WHERE corner_id IN (SELECT id FROM corners WHERE partido_id = ?)
                            """, (partido_id_eliminar,))
                            
                            # Eliminar corners del partido
                            cursor.execute("DELETE FROM corners WHERE partido_id = ?", (partido_id_eliminar,))
                            
                            # Eliminar partido
                            cursor.execute("DELETE FROM partidos WHERE id = ?", (partido_id_eliminar,))
                            
                            conn.commit()
                            st.success("Partido eliminado correctamente")
                            st.rerun()
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Error al eliminar el partido: {e}")
                        finally:
                            conn.close()
                
                # Mostrar lista de partidos
                st.subheader("Lista de Partidos")
                for partido in partidos:
                    st.write(f"ID: {partido[0]} - {partido[1]} vs {partido[2]} - {partido[3]}")
            else:
                st.info("No hay partidos registrados")