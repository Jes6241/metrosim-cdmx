import geopandas as gpd
import pandas as pd
import numpy as np
from typing import List, Dict
import os

class MetroAutomata:
    def __init__(self, shp_path: str, afluencia_path: str):
        self.metro_network = gpd.read_file(shp_path)
        
        # Cargar archivo de estaciones
        shp_dir = os.path.dirname(shp_path)
        station_path = os.path.join(shp_dir, "STC_Metro_estaciones_utm14n.shp")
        
        try:
            self.stations_network = gpd.read_file(station_path)
            print("Archivo de estaciones cargado correctamente")
        except Exception as e:
            print(f"Error al cargar estaciones: {e}")
            self.stations_network = None

        # Inicializar afluencia
        self.afluencia_base = {
            '1': 3000, '2': 2800, '3': 2600, '4': 2000,
            '5': 2200, '6': 2100, '7': 2300, '8': 2400,
            '9': 2500, 'A': 2700, 'B': 2900
        }
        
        try:
            # Cargar datos de afluencia una sola vez para inicialización
            self.afluencia_data = pd.read_csv(afluencia_path)
            print("Datos de afluencia cargados correctamente")
        except Exception as e:
            print(f"Error al cargar datos de afluencia: {e}")
            self.afluencia_data = None

        self.stations = {}
        self.initialize_stations()

    def initialize_stations(self):
        """Inicializar todas las estaciones con sus propiedades"""
        self.stations = {}
        
        if self.stations_network is not None:
            for _, station in self.stations_network.iterrows():
                try:
                    linea = str(station['LINEA'])
                    station_id = f"L{linea}_{station['CVE_EST']}"
                    coords = (station.geometry.x, station.geometry.y)
                    
                    # Obtener afluencia inicial de la base de datos
                    afluencia_inicial = 2000  # valor por defecto
                    if self.afluencia_data is not None:
                        # Buscar un dato real para esta estación
                        estacion_data = self.afluencia_data[
                            (self.afluencia_data['linea'] == f'Línea {linea}') &
                            (self.afluencia_data['estacion'] == station['NOMBRE'].strip())
                        ]
                        if not estacion_data.empty:
                            afluencia_inicial = int(estacion_data['afluencia'].iloc[0])
                    
                    self.stations[station_id] = {
                        'capacity': max(5000, afluencia_inicial * 2),  # capacidad dinámica
                        'current_people': afluencia_inicial,
                        'base_afluencia': afluencia_inicial,  # guardar afluencia base
                        'coords': coords,
                        'linea': linea,
                        'nombre': station['NOMBRE'].strip(),
                        'cve_est': station['CVE_EST']
                    }
                    print(f"Estación inicializada: {station['NOMBRE'].strip()} - Afluencia: {afluencia_inicial}")
                except Exception as e:
                    print(f"Error al procesar estación: {e}")
                    continue
        else:
            # Método alternativo usando líneas
            for _, row in self.metro_network.iterrows():
                linea = str(row['LINEA'])
                geom = row.geometry
                
                coords = []
                if hasattr(geom, 'coords'):
                    coords = list(geom.coords)
                elif hasattr(geom, 'geoms'):
                    for line in geom.geoms:
                        coords.extend(list(line.coords))
                
                for i, coord in enumerate(coords):
                    station_id = f"L{linea}_E{i}"
                    self.stations[station_id] = {
                        'capacity': 5000,
                        'current_people': np.random.randint(1000, 3000),
                        'coords': coord,
                        'linea': linea,
                        'nombre': f'Estación {station_id}'
                    }

    def step(self):
        """Actualizar estado de cada estación"""
        new_states = {}
        
        for station_id, station in self.stations.items():
            current = int(station['current_people'])
            capacity = int(station['capacity'])
            # Rango de afluencia permitido para cada celda (estación):
            # - Mínimo: 100 personas
            # - Máximo: capacidad de la estación (por defecto 5000 o afluencia_inicial*2)
            # La variación por paso es entre -1000 y +1000 (por la suma de transferencias y variación aleatoria)
            variacion_base = np.random.randint(100, 1000)  # Mayor rango de variación
            direccion = np.random.choice([-1, 1], p=[0.4, 0.6])  # Tendencia a aumentar
            variacion = variacion_base * direccion
            
            # Aplicar límites y reglas
            nuevo_valor = max(100, min(current + variacion, capacity))
            
            # Transferencias entre estaciones conectadas
            neighbors = self.get_connected_stations(station_id)
            if neighbors and np.random.random() < 0.3:  # 30% de probabilidad
                for neighbor in neighbors:
                    transfer = int(nuevo_valor * 0.2)  # Transferir hasta 20%
                    if nuevo_valor > transfer:
                        nuevo_valor -= transfer
                        self.stations[neighbor]['current_people'] = min(
                            self.stations[neighbor]['current_people'] + transfer,
                            self.stations[neighbor]['capacity']
                        )
            
            new_states[station_id] = int(nuevo_valor)
            self.stations[station_id]['current_people'] = nuevo_valor
            print(f"Estación {station['nombre']}: {current:,} -> {nuevo_valor:,}")
        
        return new_states

    def get_connected_stations(self, station_id: str) -> List[str]:
        """Obtener estaciones conectadas"""
        linea = station_id.split('_')[0][1:]  # Extraer número de línea
        station_cve = station_id.split('_')[1]  # Obtener CVE_EST completo
        
        connected = []
        if hasattr(self, 'stations_network') and self.stations_network is not None:
            # Obtener estaciones de la misma línea
            line_stations = [
                s for s in self.stations.keys() 
                if s.startswith(f"L{linea}_")
            ]
            
            # Ordenar por CVE_EST usando el código completo
            try:
                current_idx = line_stations.index(station_id)
                if current_idx > 0:
                    connected.append(line_stations[current_idx - 1])
                if current_idx < len(line_stations) - 1:
                    connected.append(line_stations[current_idx + 1])
            except ValueError:
                pass
        
        return connected

    def run_simulation(self, steps: int) -> List[Dict]:
        """Ejecutar la simulación por un número determinado de pasos"""
        results = []
        for _ in range(steps):
            self.step()
            results.append(self.get_current_state())
        return results
    
    def get_current_state(self) -> Dict:
        """Obtener el estado actual de todas las estaciones"""
        return {s: int(self.stations[s]['current_people']) for s in self.stations}

# PRINCIPAL FUNCIONAMIENTO DEL AUTOMATA CELULAR:
# - Cada estación es una celda del autómata.
# - Cada celda tiene un estado: la afluencia actual de personas.
# - En cada paso (step):
#     1. La afluencia de cada estación cambia aleatoriamente (sube o baja).
#     2. Puede haber transferencia de personas entre estaciones conectadas (vecinas).
#     3. El estado de cada estación se mantiene dentro de un rango permitido (100 a capacidad).
# - Así, el sistema evoluciona en el tiempo, mostrando cómo se distribuye y mueve la afluencia en toda la red.