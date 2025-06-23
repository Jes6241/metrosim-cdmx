# MetroSim CDMX

Simulación y visualización interactiva de la afluencia de personas en la red del Metro de la Ciudad de México usando autómatas celulares.

## Descripción

Este sistema modela cada estación del metro como una celda de un autómata celular, donde la afluencia de personas evoluciona dinámicamente en el tiempo. El sistema permite observar cómo se distribuye y mueve la afluencia en toda la red, considerando tanto variaciones aleatorias como transferencias entre estaciones conectadas. La visualización se realiza sobre un mapa interactivo, mostrando el estado de cada estación en tiempo real.

## Características principales
- Simulación basada en autómatas celulares.
- Visualización en mapa interactivo (Folium).
- Actualización dinámica de la afluencia y colores de estaciones.
- Integración de datos reales de afluencia y geolocalización.
- Código modular y fácil de extender.

## Requisitos
- Python 3.8+
- pandas
- numpy
- geopandas
- shapely
- folium
- flask

Instala las dependencias con:
```bash
pip install -r requirements.txt
```

## Archivos necesarios
- Shapefile de líneas del metro (por ejemplo: `STC_Metro_lineas_utm14n.shp`)
- Shapefile de estaciones del metro (por ejemplo: `STC_Metro_estaciones_utm14n.shp`)
- Archivo CSV de afluencia por estación (por ejemplo: `afluencia.csv`)

## Uso
1. Coloca los archivos de datos en las rutas esperadas.
2. Ejecuta el servidor Flask:
   ```bash
   python main.py
   ```
3. Abre tu navegador en [http://localhost:5000](http://localhost:5000) para ver la simulación.

## Funcionamiento del autómata celular
- Cada estación es una celda.
- El estado de cada celda es la afluencia actual de personas.
- En cada paso:
  1. La afluencia cambia aleatoriamente (sube o baja).
  2. Puede haber transferencia de personas entre estaciones conectadas.
  3. El estado se mantiene dentro de un rango permitido (100 a capacidad).

## Créditos
- Datos geográficos: Gobierno de la Ciudad de México
- Simulación y visualización: [Tu nombre o equipo]

## Licencia
Este proyecto es de uso académico y educativo.
