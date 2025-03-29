import sqlite3
import os

def get_db_connection():
    """Establece una conexión con la base de datos SQLite"""
    # Asegurarse de que el directorio de datos existe
    if not os.path.exists('data'):
        os.makedirs('data')
    
    conn = sqlite3.connect('data/corners.db')
    return conn

def dict_factory(cursor, row):
    """Convierte las filas de SQLite en diccionarios para mejor serialización"""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db_connection_dict():
    """Establece una conexión con la base de datos SQLite usando diccionarios"""
    conn = get_db_connection()
    conn.row_factory = dict_factory
    return conn

def execute_query(query, params=(), fetch_one=False, as_dict=True):
    """Ejecuta una consulta y devuelve el resultado como lista de tuplas o diccionarios"""
    if as_dict:
        conn = get_db_connection_dict()
    else:
        conn = get_db_connection()
    
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
            
        # Si necesitamos convertir diccionarios a tuplas para compatibilidad
        if as_dict and not fetch_one:
            # Convertir cada diccionario en una lista/tupla basada en valores
            result = [tuple(d.values()) for d in result]
        
        return result
    finally:
        conn.close()

def add_columns_to_corners_table():
    """
    Añade las columnas zona_caida y punto_caida a la tabla corners
    si aún no existen.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Verificar si las columnas ya existen
        cursor.execute("PRAGMA table_info(corners)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        # Añadir columna zona_caida si no existe
        if 'zona_caida' not in column_names:
            cursor.execute("ALTER TABLE corners ADD COLUMN zona_caida TEXT")
            
        # Añadir columna punto_caida si no existe
        if 'punto_caida' not in column_names:
            cursor.execute("ALTER TABLE corners ADD COLUMN punto_caida TEXT")
            
        # Guardar los cambios
        conn.commit()
        return True, "Columnas añadidas correctamente"
        
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Error al modificar la base de datos: {e}"
    finally:
        conn.close()