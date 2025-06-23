import plotly.graph_objects as go
import geopandas as gpd
import pandas as pd
import webbrowser
import os

class MetroVisualizer:
    def __init__(self, shp_path: str):
        self.metro_network = gpd.read_file(shp_path)
        # Intentar cargar archivo de estaciones
        shp_dir = os.path.dirname(shp_path)
        station_files = [f for f in os.listdir(shp_dir) if 'estacion' in f.lower() and f.endswith('.shp')]
        if station_files:
            self.stations_network = gpd.read_file(os.path.join(shp_dir, station_files[0]))
        
        self.colores = {
            '1': 'pink', '2': 'blue', '3': 'olive',
            '4': 'cyan', '5': 'yellow', '6': 'red',
            '7': 'orange', '8': 'green', '9': 'brown',
            'A': 'purple', 'B': 'gray'
        }

    def create_animation(self, states, output_path):
        # Crear figura base
        fig = go.Figure()
        
        # Crear frames para la animación
        frames = []
        for i, state in enumerate(states):
            frame_data = []
            
            # Agregar líneas del metro (solo en el primer frame)
            if i == 0:
                for linea in self.metro_network['LINEA'].unique():
                    linea_data = self.metro_network[self.metro_network['LINEA'] == linea]
                    for _, row in linea_data.iterrows():
                        x, y = row.geometry.xy
                        fig.add_trace(
                            go.Scatter(
                                x=list(x), y=list(y),
                                mode='lines',
                                line=dict(color=self.colores.get(str(linea), 'black'), width=3),
                                name=f'Línea {linea}'
                            )
                        )
            
            # Agregar estaciones con pasajeros y líneas de flujo
            for station_id, people in state.items():
                linea = station_id.split('_')[0][1:]
                station_info = next(
                    (s for s in self.stations_network.iterrows() 
                     if f"L{s[1]['LINEA']}_{s[1]['CVE_EST']}" == station_id),
                    None
                )
                
                if station_info:
                    _, station_data = station_info
                    point = station_data.geometry
                    nombre = station_data['NOMBRE'].strip()
                    
                    frame_data.append(
                        go.Scatter(
                            x=[point.x],
                            y=[point.y],
                            mode='markers+text',
                            marker=dict(
                                size=min(people/50, 40),
                                color=self.colores.get(str(linea), 'red'),
                                opacity=0.7
                            ),
                            text=f"{nombre}<br>{people} personas",
                            hoverinfo='text',
                            name=f'Estación {nombre}',
                            showlegend=False
                        )
                    )

                    # Agregar líneas de flujo entre estaciones conectadas
                    if hasattr(self, 'stations_network'):
                        connected = self.get_connected_stations(station_id)
                        for conn_id in connected:
                            if conn_id in self.stations:
                                start_point = point
                                end_point = self.stations[conn_id]['geometry']
                                
                                frame_data.append(
                                    go.Scatter(
                                        x=[start_point.x, end_point.x],
                                        y=[start_point.y, end_point.y],
                                        mode='lines',
                                        line=dict(
                                            color='rgba(255,255,255,0.5)',
                                            width=2,
                                            dash='dot'
                                        ),
                                        showlegend=False
                                    )
                                )

            frames.append(go.Frame(
                data=frame_data,
                name=str(i)
            ))
        
        # Añadir frames a la figura
        fig.frames = frames
        
        # Configurar el layout
        fig.update_layout(
            title='Simulación Metro CDMX',
            showlegend=True,
            updatemenus=[{
                'type': 'buttons',
                'showactive': False,
                'buttons': [{
                    'label': 'Play',
                    'method': 'animate',
                    'args': [None, {
                        'frame': {'duration': 1000, 'redraw': True},
                        'fromcurrent': True,
                        'transition': {'duration': 500}
                    }]
                }, {
                    'label': 'Pause',
                    'method': 'animate',
                    'args': [[None], {
                        'frame': {'duration': 0},
                        'mode': 'immediate',
                        'transition': {'duration': 0}
                    }]
                }]
            }],
            height=800,
            width=1200
        )
        
        # Configurar ejes
        fig.update_xaxes(showgrid=True)
        fig.update_yaxes(showgrid=True)
        
        # Guardar como HTML y mostrar mensaje
        fig.write_html(output_path)
        print(f"\nVisualización guardada en: {os.path.abspath(output_path)}")
        print("\nPuedes abrir el archivo de las siguientes formas:")
        print("1. Doble clic en el archivo en tu explorador")
        print("2. Arrastrarlo a tu navegador web")
        print("3. Usar el comando: python -m http.server")
        
        # Intentar abrir automáticamente en el navegador
        try:
            webbrowser.open('file://' + os.path.abspath(output_path))
        except:
            pass
