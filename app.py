import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import re
import unicodedata
from datetime import datetime

# ===================================================================
# 1. CONFIGURACIÓN DE PÁGINA Y CSS (R FLEXDASHBOARD FLATLY EXACTO)
# ===================================================================
st.set_page_config(
    page_title="PMU - Sala de Crisis Istmina",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Inyección de FontAwesome + Estilos CSS para replicar Flexdashboard
st.markdown("""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    /* Fondo general gris claro Flexdashboard */
    .stApp {
        background-color: #eaeded;
        color: #2c3e50;
        font-family: 'Lato', 'Helvetica Neue', Arial, sans-serif;
    }
    
    header {visibility: hidden !important;}
    .block-container {
        padding-top: 0rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* Barra Superior Turquesa Flatly */
    .pmu-navbar {
        background-color: #1abc9c;
        color: white;
        padding: 12px 20px;
        margin-bottom: 0px;
        font-size: 20px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }

    /* Barra de Pestañas Integrada al Banner */
    .stTabs [data-baseweb="tab-list"] {
        background-color: #1abc9c;
        padding: 0px 15px;
        gap: 2px;
        border-bottom: none;
    }
    .stTabs [data-baseweb="tab"] {
        color: rgba(255, 255, 255, 0.85) !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        padding: 10px 16px !important;
        border: none !important;
        background-color: transparent !important;
    }
    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
        background-color: #16a085 !important;
        border-bottom: 4px solid #f1c40f !important;
    }

    /* Tarjetas ValueBox con Ícono de Marca de Agua */
    .value-box {
        border-radius: 4px;
        padding: 15px 20px;
        color: white;
        position: relative;
        overflow: hidden;
        min-height: 100px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 12px;
    }
    .value-box-num {
        font-size: 40px;
        font-weight: 800;
        line-height: 1;
        margin-bottom: 4px;
    }
    .value-box-title {
        font-size: 13px;
        font-weight: 600;
        opacity: 0.95;
    }
    .value-box-icon {
        position: absolute;
        right: 15px;
        top: 50%;
        transform: translateY(-50%);
        font-size: 55px;
        opacity: 0.20;
        color: white;
    }

    /* Contenedores Blancos para Gráficos */
    div[data-testid="stVerticalBlock"] > div[data-testid="stBlock"] {
        background-color: #ffffff;
        border-radius: 4px;
        padding: 12px;
        border: 1px solid #dce4ec;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)

# Control de Autenticación
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if "expediente_buscado" not in st.session_state:
    st.session_state["expediente_buscado"] = ""

if not st.session_state["autenticado"]:
    st.title("🚨 PMU - Sala de Crisis Istmina")
    clave = st.text_input("Ingrese la clave de acceso para continuar:", type="password")
    if st.button("Ingresar"):
        if clave == "Istmina2026":
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
    st.stop()

# Helper para ValueBoxes de R
def render_value_box(numero, titulo, color_bg, icono_fa):
    st.markdown(f"""
    <div class="value-box" style="background-color: {color_bg};">
        <div>
            <div class="value-box-num">{numero}</div>
            <div class="value-box-title">{titulo}</div>
        </div>
        <i class="fa-solid {icono_fa} value-box-icon"></i>
    </div>
    """, unsafe_allow_html=True)

# ===================================================================
# 2. CARGA Y TRANSFORMACIÓN DE DATOS (MAPPING DEDUPLICADO)
# ===================================================================
def clean_col(name):
    name = unicodedata.normalize('NFD', str(name))
    name = ''.join(c for c in name if unicodedata.category(c) != 'Mn')
    name = name.lower().strip()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name

def buscar_columna(df_cols, palabras_clave):
    for col in df_cols:
        if any(kw in col for kw in palabras_clave):
            return col
    return None

def check_cond_cols(df, palabras_clave, valores_objetivo):
    cols_coincidentes = [c for c in df.columns if any(kw in c for kw in palabras_clave)]
    if not cols_coincidentes:
        return pd.Series(False, index=df.index)
    return df[cols_coincidentes].isin(valores_objetivo).any(axis=1)

@st.cache_data(ttl=30)
def cargar_datos():
    url_csv = "https://docs.google.com/spreadsheets/d/1UyHaV3J-MJ3lMnQs5lnPGIdGMTn591Tsz1aZ9_E1Z8g/gviz/tq?tqx=out:csv&sheet=Hoja%201"
    try:
        df = pd.read_csv(url_csv)
        df.columns = [clean_col(c) for c in df.columns]
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return pd.DataFrame(), {}

    # Deduplicación equivalente a R
    cols_sin_timestamp = [c for c in df.columns if c not in ["marca_temporal", "timestamp", "fecha", "fecha_corta"]]
    if cols_sin_timestamp:
        df = df.drop_duplicates(subset=cols_sin_timestamp, keep="last").reset_index(drop=True)

    # Identificación de variables principales
    col_barrio = buscar_columna(df.columns, ["barrio", "vereda"]) or "barrio_vereda"
    col_habitabilidad = buscar_columna(df.columns, ["habitabilidad", "clasificacion"]) or "clasificacion_habitabilidad"
    col_habitantes = buscar_columna(df.columns, ["total_habitantes", "habitantes", "personas"]) or "total_habitantes"
    col_ninos = buscar_columna(df.columns, ["ninos", "ninase"]) or "ninos"
    col_mayores = buscar_columna(df.columns, ["adultos_mayores", "mayores", "ancianos"]) or "adultos_mayores"
    col_discap = buscar_columna(df.columns, ["discapacidad"]) or "n_personas_discapacidad"
    col_embaraz = buscar_columna(df.columns, ["embarazada", "gestante"]) or "n_mujeres_embarazadas"
    col_propietario = buscar_columna(df.columns, ["propietario", "nombre", "afectado"]) or "nombre_propietario"
    col_telefono = buscar_columna(df.columns, ["telefono", "celular", "contacto"]) or "telefono"
    col_necesidades = buscar_columna(df.columns, ["necesidad", "requiere"]) or "necesidades_inmediatas"
    col_coords = buscar_columna(df.columns, ["coordenadas", "gps", "ubicacion"]) or "coordenadas_gps"

    df["barrio_vereda"] = df[col_barrio] if col_barrio in df.columns else "No registrado"
    df["clasificacion_habitabilidad"] = df[col_habitabilidad] if col_habitabilidad in df.columns else "Sin Clasificar"
    df["total_habitantes"] = pd.to_numeric(df[col_habitantes], errors='coerce').fillna(0).astype(int) if col_habitantes in df.columns else 0
    df["ninos"] = pd.to_numeric(df[col_ninos], errors='coerce').fillna(0).astype(int) if col_ninos in df.columns else 0
    df["adultos_mayores"] = pd.to_numeric(df[col_mayores], errors='coerce').fillna(0).astype(int) if col_mayores in df.columns else 0
    df["n_personas_discapacidad"] = pd.to_numeric(df[col_discap], errors='coerce').fillna(0).astype(int) if col_discap in df.columns else 0
    df["n_mujeres_embarazadas"] = pd.to_numeric(df[col_embaraz], errors='coerce').fillna(0).astype(int) if col_embaraz in df.columns else 0
    df["nombre_propietario"] = df[col_propietario] if col_propietario in df.columns else "No registrado"
    df["telefono"] = df[col_telefono] if col_telefono in df.columns else "No registrado"
    df["necesidades_inmediatas"] = df[col_necesidades] if col_necesidades in df.columns else "Sin especificación"

    col_fecha = buscar_columna(df.columns, ["marca_temporal", "timestamp", "fecha"])
    if col_fecha and col_fecha in df.columns:
        df["fecha_corta"] = pd.to_datetime(df[col_fecha], errors='coerce').dt.date.fillna(datetime.now().date())
    else:
        df["fecha_corta"] = datetime.now().date()

    if col_coords and col_coords in df.columns:
        coords = df[col_coords].astype(str).str.split(",", expand=True)
        df["lat"] = pd.to_numeric(coords[0], errors='coerce').fillna(5.161)
        df["lon"] = pd.to_numeric(coords[1], errors='coerce').fillna(-76.681)
    else:
        df["lat"] = 5.161
        df["lon"] = -76.681

    # Reglas ortográficas exactas de R
    def estandarizar_barrio(txt):
        txt = str(txt).lower().strip()
        if re.search(r"eduardo|santo|pep", txt): return "Eduardo Santos (La Pepé)"
        elif re.search(r"cubi|70|setenta|genoveva|lavander|chambl", txt): return "Cubis"
        elif re.search(r"camell|camelo", txt): return "Camellón"
        elif re.search(r"comerci|comers", txt): return "Comercio"
        elif re.search(r"ofel|offel", txt): return "Offel"
        elif re.search(r"independencia|valdes|valdés|valdez", txt): return "Independencia"
        elif re.search(r"diego|luis", txt): return "Diego Luis"
        elif re.search(r"carretera|carrete|san francisco|francisco", txt): return "Carretera (San Francisco)"
        elif re.search(r"agust", txt): return "San Agustín"
        elif re.search(r"pueblo|nuevo|meseta", txt): return "Pueblo Nuevo"
        return txt.title() if txt not in ["nan", ""] else "No Registrado"

    def estandarizar_sector(txt):
        txt = str(txt).lower().strip()
        if "genoveva" in txt: return "Santa Genoveva"
        elif "meseta" in txt: return "La Meseta"
        elif re.search(r"lavanderia|lavandería|lavander", txt): return "Lavandería"
        elif re.search(r"\b70\b|la 70|setenta", txt): return "La 70"
        elif re.search(r"antuco|chorro", txt): return "Chorro de Antuco"
        elif re.search(r"chamblun|chamblún|chambl", txt): return "Chamblún"
        return "Sin Sector Específico"

    df["barrio_estandar"] = df["barrio_vereda"].apply(estandarizar_barrio)
    df["sector_especifico"] = df["barrio_vereda"].apply(estandarizar_sector)

    colores_hab = {
        "Habitable": "#27ae60",
        "Habitable con restricciones": "#f1c40f",
        "No habitable": "#e74c3c",
        "Riesgo de colapso": "#8e44ad",
        "No evaluado": "#3498db",
        "Sin Clasificar": "#95a5a6",
        "No registrado": "#95a5a6"
    }
    df["color_riesgo"] = df["clasificacion_habitabilidad"].map(colores_hab).fillna("#95a5a6")

    # Necesidades
    nec_str = df["necesidades_inmediatas"].astype(str).str.lower()
    df["nec_cubierta"] = nec_str.str.contains("cubierta").astype(int)
    df["nec_materiales"] = nec_str.str.contains("materiales").astype(int)
    df["nec_muros"] = nec_str.str.contains("muros").astype(int)
    df["nec_estructura"] = nec_str.str.contains("estructural").astype(int)
    df["nec_agua"] = nec_str.str.contains("agua").astype(int)
    df["nec_alojamiento"] = nec_str.str.contains("alojamiento").astype(int)
    df["nec_alimento"] = nec_str.str.contains("alimenta").astype(int)

    # Identificación de Daños
    val_criticos = ["Severo", "Colapso", "Si", "Sí", "si", "sí"]
    val_mod_crit = ["Moderado", "Severo", "Colapso", "Si", "Sí", "si", "sí"]

    df["es_riesgo_estructural"] = check_cond_cols(df, ["cimentacion", "columnas", "vigas", "grieta_estructural"], val_criticos)
    df["es_afectacion_cubierta"] = check_cond_cols(df, ["cubierta", "techo"], val_mod_crit)
    df["es_afectacion_muros"] = check_cond_cols(df, ["muros", "fachada", "grieta_muro"], val_mod_crit)
    df["es_colapso"] = check_cond_cols(df, ["dano", "colaps", "parte_colapsada"], ["Colapso"]) | df["clasificacion_habitabilidad"].astype(str).str.contains("colapso", case=False, na=False)

    cols_sev = [c for c in df.columns if c.startswith("dano_")]
    def resumen_danos(row):
        danos = [f"{c.replace('dano_', '').title()} ({row[c]})" for c in cols_sev if row[c] in ["Severo", "Colapso"]]
        return " | ".join(danos) if danos else "Sin daños estructurales críticos"

    df["resumen_danos_criticos"] = df.apply(resumen_danos, axis=1) if cols_sev else "Sin evaluación de daños"
    return df, colores_hab

df, colores_habitabilidad = cargar_datos()

if df.empty:
    st.error("No se pudieron cargar los datos de Google Sheets.")
    st.stop()

# ===================================================================
# 3. INTERFAZ SALA DE CRISIS (ESTRUCTURA IDÉNTICA A FLEXDASHBOARD)
# ===================================================================
st.markdown('<div class="pmu-navbar">PMU - Sala de Crisis Istmina</div>', unsafe_allow_html=True)

tabs = st.tabs(["Mando Unificado", "Visor Geoespacial", "Análisis de Daños", "Vulnerabilidad", "Logística y Rescate", "Expedientes"])

# -------------------------------------------------------------------
# TAB 1: MANDO UNIFICADO
# -------------------------------------------------------------------
with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    with c1: render_value_box(len(df), "Viviendas Evaluadas", "#2c3e50", "fa-house")
    with c2: render_value_box(int(df["clasificacion_habitabilidad"].str.contains("colapso", case=False, na=False).sum()), "Riesgo Inminente (Colapso)", "#8e44ad", "fa-triangle-exclamation")
    with c3: render_value_box(int(df["total_habitantes"].sum()), "Población Total Afectada", "#e67e22", "fa-users")
    with c4: render_value_box(int(df["ninos"].sum() + df["adultos_mayores"].sum() + df["n_personas_discapacidad"].sum() + df["n_mujeres_embarazadas"].sum()), "Población Vulnerable", "#d35400", "fa-child")

    g1, g2 = st.columns(2)
    with g1:
        st.markdown("**Estado de Habitabilidad General**")
        df_hab = df["clasificacion_habitabilidad"].value_counts().reset_index()
        df_hab.columns = ["Estado", "Cantidad"]
        fig_hab = px.bar(df_hab, x="Cantidad", y="Estado", orientation='h', color="Estado", color_discrete_map=colores_habitabilidad)
        fig_hab.update_layout(template="plotly_white", showlegend=False, yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=10, t=10, b=10))
        st.plotly_chart(fig_hab, use_container_width=True)

    with g2:
        st.markdown("**Habitabilidad Consolidada por Barrio**")
        df_barrio_cnt = df.groupby('barrio_estandar').size().to_dict()
        df['barrio_etiqueta'] = df['barrio_estandar'].apply(lambda x: f"{x} ({df_barrio_cnt.get(x, 0)})")
        df_barrio = df.groupby(["barrio_etiqueta", "clasificacion_habitabilidad"]).size().reset_index(name="n")
        fig_barrio = px.bar(df_barrio, x="n", y="barrio_etiqueta", color="clasificacion_habitabilidad", orientation='h', color_discrete_map=colores_habitabilidad, labels={"n": "Cantidad de Viviendas", "barrio_etiqueta": ""})
        fig_barrio.update_layout(template="plotly_white", yaxis={'categoryorder':'total ascending'}, margin=dict(l=0, r=10, t=10, b=10))
        st.plotly_chart(fig_barrio, use_container_width=True)

    st.markdown("**Evolución Temporal de Reportes (Línea de Tiempo)**")
    df_tiempo = df.groupby("fecha_corta").size().reset_index(name="n")
    fig_tiempo = go.Figure()
    fig_tiempo.add_trace(go.Bar(x=df_tiempo["fecha_corta"], y=df_tiempo["n"], marker_color="#34495e", name="Registros"))
    fig_tiempo.add_trace(go.Scatter(x=df_tiempo["fecha_corta"], y=df_tiempo["n"], mode="lines+markers", line=dict(color="#e74c3c", width=3), name="Tendencia"))
    fig_tiempo.update_layout(template="plotly_white", showlegend=False, margin=dict(l=0, r=10, t=10, b=10))
    st.plotly_chart(fig_tiempo, use_container_width=True)

# -------------------------------------------------------------------
# TAB 2: VISOR GEOESPACIAL (CON SUB-PESTAÑAS)
# -------------------------------------------------------------------
with tabs[1]:
    col_f, col_m = st.columns([4, 6])
    with col_f:
        st.markdown("**📍 Filtros Interactivos**")
        barrio_sel = st.multiselect("Seleccione Barrio / Vereda:", options=sorted(df["barrio_estandar"].unique()))
        estado_sel = st.multiselect("Filtrar por Estado de Habitabilidad:", options=sorted(df["clasificacion_habitabilidad"].unique()))

        df_m = df.copy()
        if barrio_sel: df_m = df_m[df_m["barrio_estandar"].isin(barrio_sel)]
        if estado_sel: df_m = df_m[df_m["clasificacion_habitabilidad"].isin(estado_sel)]

        st.markdown("**🗺️ Mapa Interactivo**")
        m = folium.Map(location=[5.161, -76.681], zoom_start=14, tiles="CartoDB positron")
        for _, r in df_m.iterrows():
            html_p = f"<b>{r['nombre_propietario']}</b><br>Barrio: {r['barrio_estandar']}<br>Estado: {r['clasificacion_habitabilidad']}<br>Habitantes: {r['total_habitantes']}"
            folium.CircleMarker(
                location=[r["lat"], r["lon"]],
                radius=8,
                color=r["color_riesgo"],
                fill=True,
                fill_color=r["color_riesgo"],
                fill_opacity=0.85,
                popup=folium.Popup(html_p, max_width=250)
            ).add_to(m)
        st_folium(m, width="100%", height=420)

    with col_m:
        sub_tab1, sub_tab2 = st.tabs(["📋 Padrón Filtrado", "📊 Gráfica Viva Barrios"])
        with sub_tab1:
            st.dataframe(df_m[["nombre_propietario", "barrio_estandar", "clasificacion_habitabilidad", "total_habitantes", "telefono"]], height=400)
            propietario_sel = st.selectbox("Abrir Expediente de:", options=["-- Seleccionar --"] + sorted(df_m["nombre_propietario"].unique().tolist()))
            if propietario_sel != "-- Seleccionar --":
                if st.button("📂 Ver Expediente Completo", key="btn_exp_visor"):
                    st.session_state["expediente_buscado"] = propietario_sel
                    st.success("Cargado. Pasa a la pestaña 'Expedientes'.")

        with sub_tab2:
            fig_viva = px.histogram(df_m, x="barrio_estandar", color="clasificacion_habitabilidad", color_discrete_map=colores_habitabilidad, labels={"barrio_estandar": "", "count": "Cantidad de Viviendas Filtradas"})
            fig_viva.update_layout(template="plotly_white", margin=dict(l=0, r=10, t=10, b=10))
            st.plotly_chart(fig_viva, use_container_width=True)

# -------------------------------------------------------------------
# TAB 3: ANÁLISIS DE DAÑOS (CON SUB-PESTAÑAS)
# -------------------------------------------------------------------
with tabs[2]:
    d1, d2, d3, d4 = st.columns(4)
    with d1: render_value_box(int(df["es_riesgo_estructural"].sum()), "Riesgo Estructural Crítico", "#e74c3c", "fa-building")
    with d2: render_value_box(int(df["es_afectacion_cubierta"].sum()), "Afectación en Cubiertas", "#d35400", "fa-house")
    with d3: render_value_box(int(df["es_afectacion_muros"].sum()), "Afectación Muros / Fachada", "#f39c12", "fa-border-all")
    with d4: render_value_box(int(df["es_colapso"].sum()), "Viviendas con Colapso", "#8e44ad", "fa-circle-exclamation")

    sub_d1, sub_d2 = st.tabs(["📊 Gráficas de Daño", "🗺️ Mapa de Afectaciones"])
    
    with sub_d1:
        cd1, cd2 = st.columns(2)
        with cd1:
            st.markdown("**Severidad por Elemento**")
            cols_d = [c for c in df.columns if c.startswith("dano_")]
            if cols_d:
                df_sev = df[cols_d].melt(var_name="Elemento", value_name="Nivel")
                df_sev = df_sev[df_sev["Nivel"].isin(["Leve", "Moderado", "Severo", "Colapso"])]
                if not df_sev.empty:
                    df_sev["Elemento"] = df_sev["Elemento"].str.replace("dano_", "").str.title()
                    colores_dano = {"Leve": "#f1c40f", "Moderado": "#e67e22", "Severo": "#e74c3c", "Colapso": "#8e44ad"}
                    fig_sev = px.bar(df_sev.groupby(["Elemento", "Nivel"]).size().reset_index(name="n"), x="n", y="Elemento", color="Nivel", orientation='h', color_discrete_map=colores_dano)
                    fig_sev.update_layout(template="plotly_white", margin=dict(l=0, r=10, t=10, b=10))
                    st.plotly_chart(fig_sev, use_container_width=True)

        with cd2:
            st.markdown("**Señales Visibles Frecuentes**")
            cols_sn = [c for c in df.columns if any(p in c for p in ["grieta", "desprendimiento", "inclinacion", "colaps"])]
            if cols_sn:
                df_sn = df[cols_sn].melt(var_name="Alerta", value_name="Resp")
                df_sn = df_sn[df_sn["Resp"].astype(str).str.lower().str.contains("si|sí")]
                if not df_sn.empty:
                    df_sn["Alerta"] = df_sn["Alerta"].str.replace("_", " ").str.title()
                    fig_sn = px.bar(df_sn["Alerta"].value_counts().reset_index(name="n"), x="n", y="Alerta", orientation='h', color_discrete_sequence=["#34495e"])
                    fig_sn.update_layout(template="plotly_white", margin=dict(l=0, r=10, t=10, b=10))
                    st.plotly_chart(fig_sn, use_container_width=True)

    with sub_d2:
        col_dfiltros, col_dmapa = st.columns([3, 7])
        with col_dfiltros:
            st.markdown("**Filtros de Afectación**")
            b_dano = st.multiselect("Seleccione Barrio:", options=sorted(df["barrio_estandar"].unique()), key="bd_dano")
            s_dano = st.multiselect("Seleccione Sector:", options=sorted(df["sector_especifico"].unique()), key="sd_dano")
            
            df_mapa_danos = df[df["es_riesgo_estructural"] | df["es_afectacion_cubierta"] | df["es_afectacion_muros"] | df["es_colapso"]].copy()
            if b_dano: df_mapa_danos = df_mapa_danos[df_mapa_danos["barrio_estandar"].isin(b_dano)]
            if s_dano: df_mapa_danos = df_mapa_danos[df_mapa_danos["sector_especifico"].isin(s_dano)]

        with col_dmapa:
            m_dano = folium.Map(location=[5.161, -76.681], zoom_start=14, tiles="CartoDB positron")
            for _, r in df_mapa_danos.iterrows():
                color_point = "#8e44ad" if r["es_colapso"] else ("#e74c3c" if r["es_riesgo_estructural"] else "#f39c12")
                html_p = f"<b>{r['nombre_propietario']}</b><br>Daños: {r['resumen_danos_criticos']}"
                folium.CircleMarker(
                    location=[r["lat"], r["lon"]],
                    radius=8,
                    color=color_point,
                    fill=True,
                    fill_color=color_point,
                    fill_opacity=0.8,
                    popup=folium.Popup(html_p, max_width=250)
                ).add_to(m_dano)
            st_folium(m_dano, width="100%", height=400)

# -------------------------------------------------------------------
# TAB 4: VULNERABILIDAD
# -------------------------------------------------------------------
with tabs[3]:
    v1, v2, v3, v4 = st.columns(4)
    with v1: render_value_box(int(df["ninos"].sum()), "Total Niños y Niñas", "#16a085", "fa-child")
    with v2: render_value_box(int(df["adultos_mayores"].sum()), "Adultos Mayores", "#2980b9", "fa-user")
    with v3: render_value_box(int(df["n_personas_discapacidad"].sum()), "Personas con Discapacidad", "#8e44ad", "fa-wheelchair")
    with v4: render_value_box(int(df["n_mujeres_embarazadas"].sum()), "Mujeres Embarazadas", "#c0392b", "fa-person-pregnant")

    st.markdown("**Concentración de Población Vulnerable por Barrio**")
    df_v = df.groupby("barrio_estandar")[["ninos", "adultos_mayores", "n_personas_discapacidad", "n_mujeres_embarazadas"]].sum().reset_index()
    df_v_melt = df_v.melt(id_vars=["barrio_estandar"], var_name="Grupo", value_name="Total")
    fig_v = px.bar(df_v_melt[df_v_melt["Total"] > 0], x="Total", y="barrio_estandar", color="Grupo", barmode="group", orientation='h', color_discrete_sequence=px.colors.sequential.Viridis)
    fig_v.update_layout(template="plotly_white", margin=dict(l=0, r=10, t=10, b=10))
    st.plotly_chart(fig_v, use_container_width=True)

# -------------------------------------------------------------------
# TAB 5: LOGÍSTICA Y RESCATE
# -------------------------------------------------------------------
with tabs[4]:
    st.markdown("**Matriz de Necesidades Inmediatas Solicitadas**")
    df_n = pd.DataFrame({
        "Necesidad": ["Cubiertas/Techos", "Materiales Const.", "Reparación Muros", "Estructurales", "Agua Potable", "Alojamiento", "Alimentación"],
        "Total": [df["nec_cubierta"].sum(), df["nec_materiales"].sum(), df["nec_muros"].sum(), df["nec_estructura"].sum(), df["nec_agua"].sum(), df["nec_alojamiento"].sum(), df["nec_alimento"].sum()]
    })
    fig_n = px.bar(df_n, x="Total", y="Necesidad", orientation='h', color_discrete_sequence=["#34495e"])
    fig_n.update_layout(template="plotly_white", margin=dict(l=0, r=10, t=10, b=10))
    st.plotly_chart(fig_n, use_container_width=True)

    st.markdown("**🚨 Triage Urgente: Familias Inhabitables con Población Vulnerable**")
    df_t = df[(df["clasificacion_habitabilidad"].str.contains("colapso|no habitable", case=False, na=False)) & ((df["ninos"] > 0) | (df["adultos_mayores"] > 0) | (df["n_personas_discapacidad"] > 0))]
    st.dataframe(df_t[["barrio_estandar", "nombre_propietario", "telefono", "clasificacion_habitabilidad", "ninos", "adultos_mayores", "n_personas_discapacidad", "necesidades_inmediatas"]], use_container_width=True)

    if not df_t.empty:
        triage_sel = st.selectbox("Atender caso urgente de:", options=["-- Seleccionar --"] + sorted(df_t["nombre_propietario"].unique().tolist()))
        if triage_sel != "-- Seleccionar --":
            if st.button("📂 Abrir Expediente de Emergencia", key="btn_exp_triage"):
                st.session_state["expediente_buscado"] = triage_sel
                st.success("Caso seleccionado. Ve a la pestaña 'Expedientes'.")

# -------------------------------------------------------------------
# TAB 6: EXPEDIENTES
# -------------------------------------------------------------------
with tabs[5]:
    st.markdown("**📂 Base de Datos Completa de Evaluación**")
    col_search, col_clean = st.columns([4, 1])
    with col_search:
        busqueda = st.text_input("🔍 Buscar por Nombre de Propietario o Barrio:", value=st.session_state["expediente_buscado"])
    with col_clean:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Limpiar Filtro"):
            st.session_state["expediente_buscado"] = ""
            st.rerun()

    df_e = df.copy()
    if busqueda:
        df_e = df_e[df_e["nombre_propietario"].astype(str).str.contains(busqueda, case=False) | df_e["barrio_estandar"].astype(str).str.contains(busqueda, case=False)]

    st.dataframe(df_e, use_container_width=True)
