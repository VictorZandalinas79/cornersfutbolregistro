import hashlib
import sqlite3
from utils.db import get_db_connection

def make_hashed_password(password):
    """Crea un hash para la contraseña"""
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(username, password):
    """Verifica las credenciales del usuario"""
    if not username or not password:
        return False
    
    hashed_password = make_hashed_password(password)
    
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM usuarios WHERE username = ? AND password = ?", 
                      (username, hashed_password)).fetchone()
    conn.close()
    
    return user is not None

def register_user(username, password):
    """Registra un nuevo usuario"""
    if not username or not password:
        return False
    
    hashed_password = make_hashed_password(password)
    
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO usuarios (username, password) VALUES (?, ?)", 
                   (username, hashed_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        # El nombre de usuario ya existe
        return False
    finally:
        conn.close()