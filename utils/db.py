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