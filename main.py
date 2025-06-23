import os
from metro_simulation import MetroAutomata
import folium
from shapely.geometry import MultiLineString, LineString
from flask import Flask, Response, send_file, jsonify
import time
import json
import numpy as np

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super().default(obj)

app = Flask(__name__)
app.json_encoder = CustomJSONEncoder
automata = None

def create_map():
    # Obtener el directorio actual
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Definir ruta del archivo HTML
    output_path = os.path.join(current_dir, "metro_simulation.html")
    
    # Eliminar archivo HTML anterior si existe
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
            print(f"Archivo anterior eliminado: {output_path}")
        except Exception as e:
            print(f"No se pudo eliminar el archivo anterior: {e}")

    # Construir rutas absolutas con la estructura correcta de carpetas
    shp_path = os.path.join(current_dir, "stcmetro_shp", "stcmetro_shp", "STC_Metro_lineas_utm14n.shp")
    afluencia_path = os.path.join(current_dir, "data-2025-06-19.csv")
    
    print(f"Buscando archivo shapefile en: {shp_path}")
    print(f"Buscando archivo de afluencia en: {afluencia_path}")
    
    # Verificar si los archivos existen
    if not os.path.exists(shp_path):
        print(f"Error: No se encuentra el archivo shapefile en {shp_path}")
        print("Archivos disponibles en stcmetro_shp:")
        shp_dir = os.path.join(current_dir, "stcmetro_shp")
        if os.path.exists(shp_dir):
            print(os.listdir(shp_dir))
        return
        
    if not os.path.exists(afluencia_path):
        print(f"Error: No se encuentra el archivo de afluencia en {afluencia_path}")
        return

    # Inicializar simulación
    automata = MetroAutomata(shp_path, afluencia_path)
    
    # Ejecutar simulación
    results = automata.run_simulation(steps=10)
    
    # Convertir red de metro a WGS84 (EPSG:4326)
    automata.metro_network = automata.metro_network.to_crs(epsg=4326)
    
    # Crear mapa base centrado en CDMX con estilo más claro
    m = folium.Map(
        location=[19.432608, -99.133208],
        zoom_start=11,
        tiles='cartodbpositron',
        control_scale=True
    )
    
    # Definir colores por línea y función para color por afluencia
    linea_colores = {
        '1': '#FF1493', '2': '#0000FF', '3': '#808000',
        '4': '#00FFFF', '5': '#FFD700', '6': '#FF0000',
        '7': '#FFA500', '8': '#008000', '9': '#8B4513',
        'A': '#800080', 'B': '#696969'
    }

    def color_por_afluencia(afluencia, base_color):
        # Rango de colores para los círculos:
        # Verde: afluencia < 1500
        # Amarillo: 1500 <= afluencia < 3500
        # Rojo: afluencia >= 3500
        if afluencia < 1500:
            return "#2ecc40"  # verde
        elif afluencia < 3500:
            return "#ffd700"  # amarillo
        else:
            return "#ff4136"  # rojo

    # Agregar líneas del metro (todas las líneas)
    for _, row in automata.metro_network.iterrows():
        geom = row.geometry
        linea = str(row['LINEA'])
        color = linea_colores.get(linea, 'gray')
        
        if isinstance(geom, MultiLineString):
            for line in geom.geoms:
                x, y = line.xy
                coords = list(zip(y, x))
                # Línea base más gruesa y opaca
                folium.PolyLine(
                    coords,
                    weight=6,
                    color=color,
                    opacity=0.9,
                    popup=f"<b>Línea {linea}</b>"
                ).add_to(m)
                
                # Línea de flujo más delgada y brillante
                folium.PolyLine(
                    coords,
                    weight=4,
                    color='white',
                    opacity=0.7,
                    className=f'flow-line-{linea}'
                ).add_to(m)

    # Agregar estaciones con color dinámico según afluencia y color de línea en el borde
    for station_id, station in automata.stations.items():
        coords = station['coords']
        current = station['current_people']
        nombre = station.get('nombre', station_id)
        linea = station['linea']
        color_borde = linea_colores.get(linea, 'gray')
        color_relleno = color_por_afluencia(current, color_borde)
        
        folium.CircleMarker(
            location=[coords[1], coords[0]],
            radius=max(8, min(current/100, 25)),
            color=color_borde,
            weight=3,
            fill=True,
            fill_color=color_relleno,
            fill_opacity=0.85,
            popup=f"""
                <div style='font-family: Arial; min-width: 200px; padding: 10px;'>
                    <h3 style='margin: 0; color: {color_borde};'>{nombre}</h3>
                    <hr style='margin: 5px 0;'>
                    <b>Línea:</b> {linea}<br>
                    <b>Afluencia:</b> <span id='afluencia-{station_id}'>{current:,}</span> personas<br>
                    <b>Capacidad:</b> {station['capacity']:,} personas
                </div>
            """,
            tooltip=f"<b>{nombre}</b>",
            parse_html=True,
            attributes={
                'data-line': linea,
                'data-station-id': station_id,
                'data-people': str(current)
            }
        ).add_to(m)

    # Agregar líneas de conexión entre estaciones con animación de movimiento y color de línea
    for station_id, station in automata.stations.items():
        linea = station['linea']
        color = linea_colores.get(linea, 'gray')
        
        for neighbor_id in automata.get_connected_stations(station_id):
            if neighbor_id in automata.stations:
                station_coords = station['coords']
                neighbor_coords = automata.stations[neighbor_id]['coords']
                
                # Línea de conexión con animación de movimiento
                folium.PolyLine(
                    locations=[[station_coords[1], station_coords[0]], 
                               [neighbor_coords[1], neighbor_coords[0]]],
                    weight=3,
                    color=color,
                    opacity=0.7,
                    dash_array='10, 15',
                    className=f'connection-line-animated line-{linea}'
                ).add_to(m)

    # En el script de control, fuerza la actualización de todos los popups y colores de los círculos SVG
    time_control = """
    <style>
        @keyframes dashmove {
            to {
                stroke-dashoffset: -100;
            }
        }
        .connection-line-animated {
            stroke-dasharray: 10, 15;
            stroke-linecap: round;
            animation: dashmove 2s linear infinite;
        }
        @keyframes flow {
            0% { stroke-dashoffset: 1000; }
            100% { stroke-dashoffset: 0; }
        }
        .station-marker {
            transition: all 0.5s ease;
        }
    </style>
    <div class='control-panel'>
        <button onclick='toggleAnimation()'>Play/Pause</button>
        <span id='status'>Desconectado</span>
        <div id='info'>Actualización: <span id='countdown'>30</span>s</div>
    </div>
    <script>
        let isPlaying = false;
        let countdownInterval;
        let countdown = 30;

        function colorPorAfluencia(afluencia) {
            if (afluencia < 1500) return "#2ecc40";
            if (afluencia < 3500) return "#ffd700";
            return "#ff4136";
        }

        function updateStations() {
            fetch('/events')
                .then(response => response.json())
                .then(data => {
                    // Actualizar todos los popups abiertos y todos los círculos SVG
                    Object.entries(data).forEach(([stationId, people]) => {
                        // Actualizar el span de afluencia en todos los popups (aunque no estén abiertos)
                        document.querySelectorAll(`#afluencia-${stationId}`).forEach(span => {
                            span.textContent = people.toLocaleString();
                        });
                        // Actualizar el tamaño y color del marcador SVG
                        document.querySelectorAll('svg.leaflet-zoom-animated circle').forEach(marker => {
                            if (marker.getAttribute('data-station-id') === stationId) {
                                const newRadius = Math.max(8, Math.min(people/100, 25));
                                marker.setAttribute('r', newRadius);
                                marker.setAttribute('fill', colorPorAfluencia(people));
                            }
                        });
                    });
                })
                .catch(console.error);
        }

        function updateCountdown() {
            document.getElementById('countdown').textContent = countdown;
            countdown--;
            if (countdown < 0) {
                countdown = 30;
                if (isPlaying) updateStations();
            }
        }

        function toggleAnimation() {
            isPlaying = !isPlaying;
            const statusEl = document.getElementById('status');
            
            if (isPlaying) {
                statusEl.textContent = 'Simulación en curso';
                countdownInterval = setInterval(updateCountdown, 1000);
                updateStations();
            } else {
                statusEl.textContent = 'Simulación detenida';
                clearInterval(countdownInterval);
            }
        }
    </script>
    """
    m.get_root().html.add_child(folium.Element(time_control))

    # Guardar mapa
    m.save(output_path)
    print(f"Nuevo mapa interactivo guardado en: {output_path}")
    return output_path

@app.route('/')
def home():
    return send_file('metro_simulation.html')

@app.route('/events')
def events():
    """Endpoint para obtener actualizaciones"""
    if not automata:
        return jsonify({'error': 'Simulación no iniciada'})
    
    automata.step()
    # Convertir valores numpy a tipos Python nativos
    current_state = {
        station_id: int(people) 
        for station_id, people in automata.get_current_state().items()
    }
    return jsonify(current_state)

def main():
    global automata
    # Inicializar variables y rutas
    current_dir = os.path.dirname(os.path.abspath(__file__))
    shp_path = os.path.join(current_dir, "stcmetro_shp", "stcmetro_shp", "STC_Metro_lineas_utm14n.shp")
    afluencia_path = os.path.join(current_dir, "data-2025-06-19.csv")
    
    # Verificar si los archivos existen
    if not os.path.exists(shp_path):
        print(f"Error: No se encuentra el archivo shapefile en {shp_path}")
        return
        
    if not os.path.exists(afluencia_path):
        print(f"Error: No se encuentra el archivo de afluencia en {afluencia_path}")
        return

    # Inicializar simulación
    automata = MetroAutomata(shp_path, afluencia_path)
    
    # Crear mapa
    create_map()
    
    # Iniciar servidor Flask
    print("Iniciando servidor en http://localhost:5000")
    app.run(host='0.0.0.0', port=5000)

if __name__ == "__main__":
    main()