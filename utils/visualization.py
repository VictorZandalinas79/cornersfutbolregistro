import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle

def create_field(ax):
    """Crea un campo de fútbol simplificado para visualización de corners"""
    # Dibujar el fondo
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 70)
    ax.add_patch(plt.Rectangle((0, 0), 100, 70, fill=True, color='green', alpha=0.3))
    
    # Área de penalty
    ax.add_patch(plt.Rectangle((0, 0), 16.5, 40.3, fill=False, edgecolor='white'))
    
    # Área de portería
    ax.add_patch(plt.Rectangle((0, 0), 5.5, 18.3, fill=False, edgecolor='white'))
    
    # Semicírculo del área
    circle = plt.Circle((11, 11), 9.15, fill=False, edgecolor='white')
    ax.add_artist(circle)
    
    # Configuración final
    ax.set_aspect('equal')
    ax.axis('off')
    
    return ax

def get_role_color(role, type_pos):
    """Devuelve un color según el rol del jugador"""
    if type_pos == 'Defensivo':
        return {
            'Zona': 'red',
            'Al hombre': 'blue',
            'Poste': 'yellow',
            'Arriba': 'green'
        }.get(role, 'white')
    else:  # Ofensivo
        return {
            'Lanzador': 'purple',
            'Rematador': 'orange',
            'Bloqueador': 'cyan',
            'Arrastre': 'magenta',
            'Rechace': 'brown',
            'Atrás': 'gray'
        }.get(role, 'white')