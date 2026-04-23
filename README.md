# Dashboard de Precios de Carburantes en España

Dashboard interactivo en Streamlit que muestra los precios en tiempo real de los carburantes en todas las gasolineras de España.

## Fuente de datos

**API REST del Ministerio para la Transición Ecológica (MITECO)**
- Endpoint: `https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarworlds/PreciosCarworlds/`
- Sin API key, acceso público y gratuito
- Se actualiza varias veces al día
- ~12.000 estaciones de servicio

## Instalación y ejecución

```bash
# 1. Clona o descarga este directorio

# 2. Crea un entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Instala dependencias
pip install -r requirements.txt

# 4. Ejecuta el dashboard
streamlit run app.py
```

Se abrirá automáticamente en `http://localhost:8501`.

## Paneles incluidos

| Pestaña | Contenido |
|---|---|
| **Por CCAA** | Precio medio por comunidad autónoma (barras horizontales) |
| **Mapa** | Mapa interactivo con todas las gasolineras coloreadas por precio |
| **Distribución** | Histograma + boxplot + estadísticas descriptivas |
| **Ranking** | Top 10 más baratas, top 10 más caras, media por marca |
| **Comparativa** | Gasolina 95 vs Gasóleo A, media vs mediana por carburante |

## Funcionalidades

- **Filtros laterales**: por tipo de carburante, CCAA y provincia
- **Auto-actualización**: toggle para refrescar datos cada 30 minutos
- **Caché inteligente**: los datos se cachean 30 min para no saturar la API
- **Responsive**: funciona en escritorio y móvil

## Para la clase de Economía I

Este dashboard permite analizar:
- **Competencia y estructura de mercado**: ¿hay diferencias de precio por marca?
- **Geografía económica**: ¿por qué algunas CCAA son más caras?
- **Dispersión de precios**: ¿cómo de competitivo es el mercado?
- **Relación gasolina/gasóleo**: ¿se mueven igual?

## Licencia

Datos públicos del MITECO. Código libre para uso educativo.
