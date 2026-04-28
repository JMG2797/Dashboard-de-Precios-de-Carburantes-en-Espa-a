"""
Dashboard de Precios de Carburantes en España
==============================================
Fuente: API REST del Ministerio para la Transición Ecológica (MITECO)
Autor: Proyecto para Economía I
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import numpy as np
import unicodedata
from datetime import datetime
import warnings

# Desactivar advertencias SSL para requests
warnings.filterwarnings('ignore', category=requests.packages.urllib3.exceptions.InsecureRequestWarning)

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA (DEBE SER LO PRIMERO)
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Carburantes España",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# ESTILOS CSS PERSONALIZADOS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;600&display=swap');

    /* Global */
    .stApp {
        font-family: 'DM Sans', sans-serif;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #0f3460;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetric"] label {
        color: #a8b2d1 !important;
        font-size: 0.85rem !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #e6f1ff !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 1.8rem !important;
        font-weight: 600 !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a1a 0%, #1a1a2e 100%);
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li {
        color: #a8b2d1;
    }

    /* Headers */
    h1, h2, h3 {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
    }

    /* Divider */
    .custom-divider {
        height: 3px;
        background: linear-gradient(90deg, #e94560, #0f3460, #533483);
        border-radius: 2px;
        margin: 0.5rem 0 1.5rem 0;
    }

    /* Footer */
    .footer-text {
        text-align: center;
        color: #4a5568;
        font-size: 0.75rem;
        margin-top: 3rem;
        padding: 1rem;
        border-top: 1px solid #2d3748;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FUNCIONES DE DATOS
# ─────────────────────────────────────────────

API_BASE = "https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes"

# Mapeo de endpoints de la API (ACTUALIZADO 2024)
ENDPOINTS = {
    "estaciones": f"{API_BASE}/PreciosCarburantes/EstacionesTerrestres/",
    "productos": f"{API_BASE}/PreciosCarburantes/Listados/ProductosPetroliferos/",
    "ccaa": f"{API_BASE}/PreciosCarburantes/Listados/ComunidadesAutonomas/",
    "provincias": f"{API_BASE}/PreciosCarburantes/Listados/Provincias/",
    "municipios": f"{API_BASE}/PreciosCarburantes/Listados/MunicipiosPorProvincia/",
}

# Columnas clave de la API y sus renombramientos
COLUMN_MAP = {
    "Rótulo": "rotulo",
    "Dirección": "direccion",
    "C.P.": "cp",
    "Localidad": "localidad",
    "Municipio": "municipio",
    "Provincia": "provincia",
    "IDCCAA": "id_ccaa",
    "Latitud": "latitud",
    "Longitud (WGS84)": "longitud",
    "Precio Gasolina 95 E5": "gasolina_95",
    "Precio Gasóleo A": "gasoleo_a",
    "Precio Gasóleo Premium": "gasoleo_premium",
    "Precio Gasolina 98 E5": "gasolina_98",
    "Precio Gas Natural Comprimido": "gnc",
    "Precio Gases licuados del petróleo": "glp",
    "Horario": "horario",
    "Tipo Venta": "tipo_venta",
}


def normalize_col_name(name):
    if not isinstance(name, str):
        return ""
    normalized = unicodedata.normalize("NFKD", name)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.lower()
    for char in " .,-()[]/\'":
        normalized = normalized.replace(char, "")
    return normalized

# Nombres de CCAA por ID
CCAA_NOMBRES = {
    "01": "Andalucía", "02": "Aragón", "03": "Asturias",
    "04": "Baleares", "05": "Canarias", "06": "Cantabria",
    "07": "Castilla y León", "08": "Castilla-La Mancha",
    "09": "Cataluña", "10": "Comunidad Valenciana",
    "11": "Extremadura", "12": "Galicia", "13": "Madrid",
    "14": "Murcia", "15": "Navarra", "16": "País Vasco",
    "17": "La Rioja", "18": "Ceuta", "19": "Melilla",
}


@st.cache_data(ttl=1800)  # Cache 30 minutos
def cargar_datos():
    """Descarga y procesa los datos de la API del Ministerio."""
    import ssl
    from urllib3.exceptions import InsecureRequestWarning
    
    # Desactivar advertencias de SSL no verificado
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    
    # Crear una sesión con desactivación de SSL verificado
    session = requests.Session()
    session.verify = False
    
    # Crear un contexto SSL que no verifique certificados
    try:
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
    except:
        ssl_context = None
    
    try:
        # Intentar con múltiples configuraciones si es necesario
        for intento in range(3):
            try:
                response = session.get(
                    ENDPOINTS["estaciones"],
                    headers={"Accept": "application/json"},
                    timeout=30,
                    verify=False,
                )
                response.raise_for_status()
                data = response.json()
                break  # Éxito, salir del loop
            except requests.exceptions.SSLError as e:
                if intento < 2:
                    continue
                else:
                    raise

        # La respuesta tiene una clave 'ListaEESSPrecio' con las estaciones
        estaciones = data.get("ListaEESSPrecio", [])
        if not estaciones:
            st.error("No se recibieron datos de estaciones.")
            return pd.DataFrame()

        df = pd.DataFrame(estaciones)
        df.columns = [col.strip() if isinstance(col, str) else col for col in df.columns]

        # Renombrar columnas existentes con normalización de nombres
        normalized_columns = {normalize_col_name(col): col for col in df.columns}
        rename = {}
        for raw_name, std_name in COLUMN_MAP.items():
            normalized_raw = normalize_col_name(raw_name)
            if normalized_raw in normalized_columns:
                rename[normalized_columns[normalized_raw]] = std_name
        df = df.rename(columns=rename)

        # Convertir precios (usan coma como decimal)
        precio_cols = [
            "gasolina_95", "gasoleo_a", "gasoleo_premium",
            "gasolina_98", "gnc", "glp",
        ]
        for col in precio_cols:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                    .str.strip()
                )
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Convertir coordenadas
        for coord in ["latitud", "longitud"]:
            if coord in df.columns:
                df[coord] = (
                    df[coord]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                )
                df[coord] = pd.to_numeric(df[coord], errors="coerce")

        # Añadir nombre de CCAA
        if "id_ccaa" in df.columns:
            df["ccaa"] = df["id_ccaa"].astype(str).str.zfill(2).map(CCAA_NOMBRES)

        # Fecha de actualización desde la respuesta
        fecha = data.get("Fecha", "No disponible")
        nota = data.get("Nota", "")

        return df, fecha, nota

    except requests.exceptions.RequestException as e:
        st.error(f"Error al conectar con la API: {e}")
        return pd.DataFrame(), "Error", ""
    except Exception as e:
        st.error(f"Error procesando datos: {e}")
        return pd.DataFrame(), "Error", ""


def formato_precio(valor):
    """Formatea un precio en euros."""
    if pd.isna(valor):
        return "N/D"
    return f"{valor:.3f} €/L"


# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────
resultado = cargar_datos()

if isinstance(resultado, tuple) and len(resultado) == 3:
    df, fecha_actualizacion, nota = resultado
else:
    df = pd.DataFrame()
    fecha_actualizacion = "Error"
    nota = ""

if df.empty:
    st.warning("⚠️ No se pudieron cargar datos. Verifica tu conexión a internet.")
    st.info(
        "La API del Ministerio (sedeaplicaciones.minetur.gob.es) "
        "debe ser accesible desde tu red."
    )
    st.stop()


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⛽ Filtros")
    st.markdown(f"**Última actualización:**  \n`{fecha_actualizacion}`")
    st.markdown("---")

    # Selector de carburante principal
    available_carburantes = [
        c for c in ["gasolina_95", "gasoleo_a", "gasolina_98", "gasoleo_premium"]
        if c in df.columns
    ]
    if not available_carburantes:
        st.error("No se encontraron columnas de carburante válidas en los datos.")
        st.stop()

    carburante = st.selectbox(
        "Tipo de carburante",
        options=available_carburantes,
        format_func=lambda x: {
            "gasolina_95": "🟢 Gasolina 95 E5",
            "gasoleo_a": "🔵 Gasóleo A",
            "gasolina_98": "🟡 Gasolina 98 E5",
            "gasoleo_premium": "🟠 Gasóleo Premium",
        }.get(x, x),
    )

    # Filtro CCAA
    ccaa_disponibles = sorted(df["ccaa"].dropna().unique().tolist())
    ccaa_sel = st.multiselect(
        "Comunidades Autónomas",
        options=ccaa_disponibles,
        default=[],
        placeholder="Todas (sin filtrar)",
    )

    # Filtro provincia
    if ccaa_sel:
        provincias_disp = sorted(
            df[df["ccaa"].isin(ccaa_sel)]["provincia"].dropna().unique().tolist()
        )
    else:
        provincias_disp = sorted(df["provincia"].dropna().unique().tolist())

    provincia_sel = st.multiselect(
        "Provincias",
        options=provincias_disp,
        default=[],
        placeholder="Todas (sin filtrar)",
    )

    st.markdown("---")

    # Auto-refresh
    auto_refresh = st.toggle("Auto-actualizar (30 min)", value=False)
    if auto_refresh:
        st.markdown("*El dashboard se recargará automáticamente.*")
        import time
        # Streamlit re-run every 30 min
        st.markdown(
            '<meta http-equiv="refresh" content="1800">',
            unsafe_allow_html=True,
        )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 Actualizar ahora", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col_btn2:
        if st.button("🔐 Forzar sin SSL", use_container_width=True):
            st.cache_data.clear()
            st.session_state['force_ssl_bypass'] = True
            st.rerun()

    st.markdown("---")
    st.markdown(
        "**Fuente:** [MITECO – Geoportal]"
        "(https://geoportalgasolineras.es/)  \n"
        "Datos públicos bajo licencia abierta."
    )


# ─────────────────────────────────────────────
# APLICAR FILTROS
# ─────────────────────────────────────────────
df_filtrado = df.copy()

if ccaa_sel:
    df_filtrado = df_filtrado[df_filtrado["ccaa"].isin(ccaa_sel)]
if provincia_sel:
    df_filtrado = df_filtrado[df_filtrado["provincia"].isin(provincia_sel)]

# Filtrar solo estaciones con precio válido para el carburante seleccionado
df_con_precio = df_filtrado[df_filtrado[carburante].notna()].copy()

NOMBRES_BONITOS = {
    "gasolina_95": "Gasolina 95 E5",
    "gasoleo_a": "Gasóleo A",
    "gasolina_98": "Gasolina 98 E5",
    "gasoleo_premium": "Gasóleo Premium",
}

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown("# ⛽ Precios de Carburantes en España")
st.markdown(f"### {NOMBRES_BONITOS[carburante]}")
st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPIs PRINCIPALES
# ─────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

precio_medio = df_con_precio[carburante].mean()
precio_min = df_con_precio[carburante].min()
precio_max = df_con_precio[carburante].max()
n_estaciones = len(df_con_precio)

col1.metric("Precio medio", formato_precio(precio_medio))
col2.metric("Precio mínimo", formato_precio(precio_min))
col3.metric("Precio máximo", formato_precio(precio_max))
col4.metric("Estaciones", f"{n_estaciones:,}")

st.markdown("")

# ─────────────────────────────────────────────
# PESTAÑAS PRINCIPALES
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Por Comunidad Autónoma",
    "🗺️ Mapa",
    "📈 Distribución",
    "🏷️ Ranking Gasolineras",
    "⚖️ Comparativa",
])


# ── TAB 1: POR CCAA ──────────────────────────
with tab1:
    st.markdown("#### Precio medio por Comunidad Autónoma")

    medias_ccaa = (
        df_con_precio.groupby("ccaa")[carburante]
        .agg(["mean", "median", "count"])
        .reset_index()
        .sort_values("mean", ascending=True)
    )
    medias_ccaa.columns = ["CCAA", "Media", "Mediana", "Estaciones"]

    fig_ccaa = px.bar(
        medias_ccaa,
        x="Media",
        y="CCAA",
        orientation="h",
        color="Media",
        color_continuous_scale="RdYlGn_r",
        hover_data={"Mediana": ":.3f", "Estaciones": True, "Media": ":.3f"},
        labels={"Media": "€/L", "CCAA": ""},
    )
    fig_ccaa.update_layout(
        height=550,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"),
        coloraxis_showscale=False,
        margin=dict(l=10, r=30, t=10, b=10),
    )
    fig_ccaa.add_vline(
        x=precio_medio,
        line_dash="dash",
        line_color="#e94560",
        annotation_text=f"Media nacional: {precio_medio:.3f}€",
        annotation_font_color="#e94560",
    )
    st.plotly_chart(fig_ccaa, use_container_width=True)

    # Tabla resumen
    with st.expander("📋 Ver tabla detallada"):
        medias_ccaa_fmt = medias_ccaa.copy()
        medias_ccaa_fmt["Media"] = medias_ccaa_fmt["Media"].map(lambda x: f"{x:.3f} €")
        medias_ccaa_fmt["Mediana"] = medias_ccaa_fmt["Mediana"].map(lambda x: f"{x:.3f} €")
        st.dataframe(
            medias_ccaa_fmt.sort_values("CCAA"),
            use_container_width=True,
            hide_index=True,
        )


# ── TAB 2: MAPA ──────────────────────────────
with tab2:
    st.markdown("#### Mapa de estaciones de servicio")
    st.caption("Cada punto representa una gasolinera. El color indica el precio.")

    # Limitar a muestra si hay muchas estaciones (rendimiento)
    MAX_MAP_POINTS = 3000
    if len(df_con_precio) > MAX_MAP_POINTS:
        df_mapa = df_con_precio.sample(MAX_MAP_POINTS, random_state=42)
        st.info(f"Mostrando {MAX_MAP_POINTS:,} de {len(df_con_precio):,} estaciones (muestra aleatoria para rendimiento).")
    else:
        df_mapa = df_con_precio

    df_mapa_valid = df_mapa.dropna(subset=["latitud", "longitud"])

    fig_mapa = px.scatter_map(
        df_mapa_valid,
        lat="latitud",
        lon="longitud",
        color=carburante,
        color_continuous_scale="RdYlGn_r",
        size_max=8,
        zoom=5,
        center={"lat": 40.0, "lon": -3.7},
        hover_name="rotulo" if "rotulo" in df_mapa_valid.columns else None,
        hover_data={
            carburante: ":.3f",
            "provincia": True,
            "municipio": True,
        },
        labels={carburante: "€/L"},
        map_style="carto-darkmatter",
    )
    fig_mapa.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="DM Sans"),
    )
    st.plotly_chart(fig_mapa, use_container_width=True)


# ── TAB 3: DISTRIBUCIÓN ──────────────────────
with tab3:
    col_hist, col_box = st.columns(2)

    with col_hist:
        st.markdown("#### Histograma de precios")
        fig_hist = px.histogram(
            df_con_precio,
            x=carburante,
            nbins=60,
            labels={carburante: "€/L"},
            color_discrete_sequence=["#e94560"],
        )
        fig_hist.add_vline(
            x=precio_medio,
            line_dash="dash",
            line_color="#64ffda",
            annotation_text=f"Media: {precio_medio:.3f}€",
            annotation_font_color="#64ffda",
        )
        fig_hist.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
            yaxis_title="Nº estaciones",
            height=400,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_box:
        st.markdown("#### Boxplot por CCAA")
        # Top 10 CCAA por nº de estaciones para legibilidad
        top_ccaa = (
            df_con_precio["ccaa"]
            .value_counts()
            .head(10)
            .index.tolist()
        )
        df_box = df_con_precio[df_con_precio["ccaa"].isin(top_ccaa)]

        fig_box = px.box(
            df_box,
            x="ccaa",
            y=carburante,
            color="ccaa",
            labels={carburante: "€/L", "ccaa": ""},
        )
        fig_box.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
            showlegend=False,
            xaxis_tickangle=-45,
            height=400,
        )
        st.plotly_chart(fig_box, use_container_width=True)

    # Estadísticas descriptivas
    st.markdown("#### Estadísticas descriptivas")
    stats = df_con_precio[carburante].describe()
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    col_s1.metric("Desviación típica", f"{stats['std']:.4f} €")
    col_s2.metric("Percentil 25", f"{stats['25%']:.3f} €")
    col_s3.metric("Mediana (P50)", f"{stats['50%']:.3f} €")
    col_s4.metric("Percentil 75", f"{stats['75%']:.3f} €")


# ── TAB 4: RANKING ────────────────────────────
with tab4:
    col_bar, col_car = st.columns(2)

    with col_bar:
        st.markdown("#### 🏆 Top 10 más baratas")
        top_baratas = (
            df_con_precio
            .nsmallest(10, carburante)
            [["rotulo", "municipio", "provincia", carburante]]
            .reset_index(drop=True)
        )
        top_baratas.index = top_baratas.index + 1
        top_baratas.columns = ["Rótulo", "Municipio", "Provincia", "Precio (€/L)"]
        top_baratas["Precio (€/L)"] = top_baratas["Precio (€/L)"].map(
            lambda x: f"{x:.3f}"
        )
        st.dataframe(top_baratas, use_container_width=True)

    with col_car:
        st.markdown("#### 💸 Top 10 más caras")
        top_caras = (
            df_con_precio
            .nlargest(10, carburante)
            [["rotulo", "municipio", "provincia", carburante]]
            .reset_index(drop=True)
        )
        top_caras.index = top_caras.index + 1
        top_caras.columns = ["Rótulo", "Municipio", "Provincia", "Precio (€/L)"]
        top_caras["Precio (€/L)"] = top_caras["Precio (€/L)"].map(
            lambda x: f"{x:.3f}"
        )
        st.dataframe(top_caras, use_container_width=True)

    # Media por marca (rótulo)
    st.markdown("#### Precio medio por marca (top 15 por nº de estaciones)")
    marcas = (
        df_con_precio.groupby("rotulo")
        .agg(
            precio_medio=(carburante, "mean"),
            n_estaciones=(carburante, "count"),
        )
        .reset_index()
        .sort_values("n_estaciones", ascending=False)
        .head(15)
        .sort_values("precio_medio")
    )

    fig_marcas = px.bar(
        marcas,
        x="precio_medio",
        y="rotulo",
        orientation="h",
        color="precio_medio",
        color_continuous_scale="RdYlGn_r",
        hover_data={"n_estaciones": True, "precio_medio": ":.3f"},
        labels={"precio_medio": "€/L", "rotulo": "", "n_estaciones": "Estaciones"},
    )
    fig_marcas.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"),
        coloraxis_showscale=False,
        height=450,
        margin=dict(l=10, r=30, t=10, b=10),
    )
    st.plotly_chart(fig_marcas, use_container_width=True)


# ── TAB 5: COMPARATIVA ───────────────────────
with tab5:
    st.markdown("#### Comparativa entre carburantes")

    carburantes_disp = ["gasolina_95", "gasoleo_a", "gasolina_98", "gasoleo_premium"]
    carburantes_nombres = {
        "gasolina_95": "Gasolina 95",
        "gasoleo_a": "Gasóleo A",
        "gasolina_98": "Gasolina 98",
        "gasoleo_premium": "Gasóleo Premium",
    }

    # Medias nacionales de cada carburante
    medias_nacionales = []
    for c in carburantes_disp:
        if c in df_filtrado.columns:
            vals = df_filtrado[c].dropna()
            if len(vals) > 0:
                medias_nacionales.append({
                    "Carburante": carburantes_nombres[c],
                    "Media": vals.mean(),
                    "Mediana": vals.median(),
                    "Mínimo": vals.min(),
                    "Máximo": vals.max(),
                    "Estaciones": len(vals),
                })

    df_comp = pd.DataFrame(medias_nacionales)

    if not df_comp.empty:
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name="Media",
            x=df_comp["Carburante"],
            y=df_comp["Media"],
            marker_color="#e94560",
            text=df_comp["Media"].map(lambda x: f"{x:.3f}€"),
            textposition="outside",
        ))
        fig_comp.add_trace(go.Bar(
            name="Mediana",
            x=df_comp["Carburante"],
            y=df_comp["Mediana"],
            marker_color="#0f3460",
            text=df_comp["Mediana"].map(lambda x: f"{x:.3f}€"),
            textposition="outside",
        ))
        fig_comp.update_layout(
            barmode="group",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
            yaxis_title="€/L",
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    # Scatter gasolina vs gasóleo por CCAA
    st.markdown("#### Gasolina 95 vs Gasóleo A por CCAA")

    if "gasolina_95" in df_filtrado.columns and "gasoleo_a" in df_filtrado.columns:
        scatter_data = (
            df_filtrado.groupby("ccaa")
            .agg(
                g95=("gasolina_95", "mean"),
                ga=("gasoleo_a", "mean"),
                n=("gasolina_95", "count"),
            )
            .dropna()
            .reset_index()
        )

        fig_scatter = px.scatter(
            scatter_data,
            x="g95",
            y="ga",
            text="ccaa",
            size="n",
            size_max=30,
            labels={
                "g95": "Gasolina 95 (€/L)",
                "ga": "Gasóleo A (€/L)",
                "ccaa": "CCAA",
                "n": "Estaciones",
            },
            color_discrete_sequence=["#e94560"],
        )
        fig_scatter.update_traces(textposition="top center", textfont_size=10)
        fig_scatter.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
            height=500,
        )
        # Línea y=x
        rng = [
            min(scatter_data["g95"].min(), scatter_data["ga"].min()) - 0.02,
            max(scatter_data["g95"].max(), scatter_data["ga"].max()) + 0.02,
        ]
        fig_scatter.add_trace(go.Scatter(
            x=rng, y=rng,
            mode="lines",
            line=dict(dash="dot", color="gray"),
            name="Precio igual",
            showlegend=True,
        ))
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.caption(
            "Los puntos por encima de la línea indican que el gasóleo A "
            "es más caro que la gasolina 95 en esa comunidad (poco habitual)."
        )


# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown(
    '<div class="footer-text">'
    "Dashboard de Carburantes España · Economía I · "
    "Datos: Ministerio para la Transición Ecológica (MITECO) · "
    f"Última carga: {fecha_actualizacion}"
    "</div>",
    unsafe_allow_html=True,
)
