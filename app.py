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
# CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ===================================================================
st.set_page_config(
    page_title="PMU - Sala de Crisis Istmina",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

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

# ===================================================================
# LIMPIADOR DE ENCABEZADOS IDENTICO A R (janitor::clean_names)
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
    """Evalua condiciones sobre una lista de columnas garantizando un DataFrame de Pandas"""
    cols_coincidentes = [c for c in df.columns if any(kw in c for kw in palabras_clave)]
    if not cols_coincidentes:
        return pd.Series(False, index=df.index)
    return df[cols_coincidentes].isin(valores_objetivo).any(axis=1)

# ===================================================================
# CARGA Y TRATAMIENTO DE DATOS (REFRESCO CADA 30 SEGUNDOS)
# ===================================================================
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

    # Mapeo de columnas principales
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

    # Homologación de variables
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

    # Fechas
    col_fecha = buscar_columna(df.columns, ["marca_temporal", "timestamp", "fecha"])
    if col_fecha and col_fecha in df.columns:
        df["fecha_corta"] = pd.to_datetime(df[col_fecha], errors='coerce').dt.date.fillna(datetime.now().date())
    else:
        df["fecha_corta"] = datetime.now().date()

    # Coordenadas
    if col_coords and col_coords in df.columns:
        coords = df[col_coords].astype(str).str.split(",", expand=True)
        df["lat"] = pd.to_numeric(coords[0], errors='coerce').fillna(5.161)
        df["lon"] = pd.to_numeric(coords[1], errors='coerce').fillna(-76.681)
    else:
        df["lat"] = 5.161
        df["lon"] = -76.681

    # Reglas ortográficas de Barrios y Sectores
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

    # Banderas de Necesidades
    nec_str = df["necesidades_inmediatas"].astype(str).str.lower()
    df["nec_cubierta"] = nec_str.str.contains("cubierta").astype(int)
    df["nec_materiales"] = nec_str.str.contains("materiales").astype(int)
    df["nec_muros"] = nec_str.str.contains("muros").astype(int)
    df["nec_estructura"] = nec_str.str.contains("estructural").astype(int)
    df["nec_agua"] = nec_str.str.contains("agua").astype(int)
    df["nec_alojamiento"] = nec_str.str.contains("alojamiento").astype(int)
    df["nec_alimento"] = nec_str.str.contains("alimenta").astype(int)

    # Identificación segura de Daños (evitando errores de Pandas Series/DataFrame)
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
    st.error("No se pudieron cargar los datos de Google Sheets. Verifique el enlace público.")
    st.stop()

# ===================================================================
# INTERFAZ DENTRO DE LA SALA DE CRISIS
# ===================================================================
st.title("🚨 PMU - Sala de Crisis Istmina")
tabs = st.tabs(["📊 Mando Unificado", "🗺️ Visor Geoespacial", "🏗️ Análisis de Daños", "👶 Vulnerabilidad", "📦 Logística y Rescate", "📂 Expedientes"])

# TAB 1: MANDO UNIFICADO
with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Viviendas Evaluadas", len(df))
    colapso_cnt = int(df["clasificacion_habitabilidad"].str.contains("colapso", case=False, na=False).sum())
    c2.metric("Riesgo Inminente (Colapso)", colapso_cnt)
    c3.metric("Población Total Afectada", int(df["total_habitantes"].sum()))
    vuln_cnt = int(df["ninos"].sum() + df["adultos_mayores"].sum() + df["n_personas_discapacidad"].sum() + df["n_mujeres_embarazadas"].sum())
    c4.metric("Población Vulnerable", vuln_cnt)

    st.markdown("---")
    g1, g2 = st.columns(2)

    with g1:
        st.subheader("Estado de Habitabilidad General")
        df_hab = df["clasificacion_habitabilidad"].value_counts().reset_index()
        df_hab.columns = ["Estado", "Cantidad"]
        fig_hab = px.bar(df_hab, x="Cantidad", y="Estado", orientation='h', color="Estado", color_discrete_map=colores_habitabilidad)
        fig_hab.update_layout(showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_hab, use_container_width=True)

    with g2:
        st.subheader("Habitabilidad Consolidada por Barrio")
        df_barrio = df.groupby(["barrio_estandar", "clasificacion_habitabilidad"]).size().reset_index(name="n")
        fig_barrio = px.bar(df_barrio, x="n", y="barrio_estandar", color="clasificacion_habitabilidad", orientation='h', color_discrete_map=colores_habitabilidad, labels={"n": "Cantidad de Viviendas", "barrio_estandar": ""})
        fig_barrio.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_barrio, use_container_width=True)

    st.subheader("Evolución Temporal de Reportes")
    df_tiempo = df.groupby("fecha_corta").size().reset_index(name="n")
    fig_tiempo = px.line(df_tiempo, x="fecha_corta", y="n", markers=True, labels={"fecha_corta": "Fecha", "n": "Evaluaciones"})
    fig_tiempo.update_traces(line_color="#e74c3c")
    st.plotly_chart(fig_tiempo, use_container_width=True)

# TAB 2: VISOR GEOESPACIAL
with tabs[1]:
    col_f, col_m = st.columns([1, 2])
    with col_f:
        st.subheader("📍 Filtros Interactivos")
        barrio_sel = st.multiselect("Seleccione Barrio / Vereda:", options=sorted(df["barrio_estandar"].unique()))
        estado_sel = st.multiselect("Filtrar por Estado:", options=sorted(df["clasificacion_habitabilidad"].unique()))

        df_m = df.copy()
        if barrio_sel: df_m = df_m[df_m["barrio_estandar"].isin(barrio_sel)]
        if estado_sel: df_m = df_m[df_m["clasificacion_habitabilidad"].isin(estado_sel)]

        st.subheader("📋 Padrón Filtrado")
        st.dataframe(df_m[["nombre_propietario", "barrio_estandar", "clasificacion_habitabilidad", "total_habitantes"]], height=250)

    with col_m:
        st.subheader("🗺️ Mapa Interactivo")
        m = folium.Map(location=[5.161, -76.681], zoom_start=14)
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
        st_folium(m, width="100%", height=500)

# TAB 3: ANÁLISIS DE DAÑOS
with tabs[2]:
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Riesgo Estructural Crítico", int(df["es_riesgo_estructural"].sum()))
    d2.metric("Afectación en Cubiertas", int(df["es_afectacion_cubierta"].sum()))
    d3.metric("Afectación Muros / Fachada", int(df["es_afectacion_muros"].sum()))
    d4.metric("Viviendas con Colapso", int(df["es_colapso"].sum()))

    st.markdown("---")
    cd1, cd2 = st.columns(2)
    with cd1:
        st.subheader("Severidad por Elemento")
        cols_d = [c for c in df.columns if c.startswith("dano_")]
        if cols_d:
            df_sev = df[cols_d].melt(var_name="Elemento", value_name="Nivel")
            df_sev = df_sev[df_sev["Nivel"].isin(["Leve", "Moderado", "Severo", "Colapso"])]
            if not df_sev.empty:
                df_sev["Elemento"] = df_sev["Elemento"].str.replace("dano_", "").str.title()
                fig_sev = px.bar(df_sev.groupby(["Elemento", "Nivel"]).size().reset_index(name="n"), x="n", y="Elemento", color="Nivel", orientation='h')
                st.plotly_chart(fig_sev, use_container_width=True)
            else:
                st.info("Sin desglose detallado de gravedad de daños.")
        else:
            st.info("Sin registros de gravedad por elemento.")

    with cd2:
        st.subheader("Señales Visibles Frecuentes")
        cols_sn = [c for c in df.columns if any(p in c for p in ["grieta", "desprendimiento", "inclinacion", "colaps"])]
        if cols_sn:
            df_sn = df[cols_sn].melt(var_name="Alerta", value_name="Resp")
            df_sn = df_sn[df_sn["Resp"].astype(str).str.lower().str.contains("si|sí")]
            if not df_sn.empty:
                df_sn["Alerta"] = df_sn["Alerta"].str.replace("_", " ").str.title()
                fig_sn = px.bar(df_sn["Alerta"].value_counts().reset_index(name="n"), x="n", y="Alerta", orientation='h', color_discrete_sequence=["#34495e"])
                st.plotly_chart(fig_sn, use_container_width=True)
            else:
                st.info("Sin alertas visibles confirmadas.")

# TAB 4: VULNERABILIDAD
with tabs[3]:
    v1, v2, v3, v4 = st.columns(4)
    v1.metric("Total Niños y Niñas", int(df["ninos"].sum()))
    v2.metric("Adultos Mayores", int(df["adultos_mayores"].sum()))
    v3.metric("Personas con Discapacidad", int(df["n_personas_discapacidad"].sum()))
    v4.metric("Mujeres Embarazadas", int(df["n_mujeres_embarazadas"].sum()))

    st.markdown("---")
    st.subheader("Concentración de Población Vulnerable por Barrio")
    df_v = df.groupby("barrio_estandar")[["ninos", "adultos_mayores", "n_personas_discapacidad", "n_mujeres_embarazadas"]].sum().reset_index()
    fig_v = px.bar(df_v.melt(id_vars=["barrio_estandar"], var_name="Grupo", value_name="Total"), x="Total", y="barrio_estandar", color="Grupo", barmode="group", orientation='h')
    st.plotly_chart(fig_v, use_container_width=True)

# TAB 5: LOGÍSTICA Y RESCATE
with tabs[4]:
    st.subheader("Matriz de Necesidades Inmediatas Solicitadas")
    df_n = pd.DataFrame({
        "Necesidad": ["Cubiertas/Techos", "Materiales Const.", "Reparación Muros", "Estructurales", "Agua Potable", "Alojamiento", "Alimentación"],
        "Total": [df["nec_cubierta"].sum(), df["nec_materiales"].sum(), df["nec_muros"].sum(), df["nec_estructura"].sum(), df["nec_agua"].sum(), df["nec_alojamiento"].sum(), df["nec_alimento"].sum()]
    })
    fig_n = px.bar(df_n, x="Total", y="Necesidad", orientation='h', color_discrete_sequence=["#34495e"])
    st.plotly_chart(fig_n, use_container_width=True)

    st.subheader("🚨 Triage Urgente: Familias Inhabitables con Población Vulnerable")
    df_t = df[(df["clasificacion_habitabilidad"].str.contains("colapso|no habitable", case=False, na=False)) & ((df["ninos"] > 0) | (df["adultos_mayores"] > 0) | (df["n_personas_discapacidad"] > 0))]
    st.dataframe(df_t[["barrio_estandar", "nombre_propietario", "telefono", "clasificacion_habitabilidad", "ninos", "adultos_mayores", "n_personas_discapacidad", "necesidades_inmediatas"]], use_container_width=True)

# TAB 6: EXPEDIENTES
with tabs[5]:
    st.subheader("📂 Base de Datos Completa de Evaluación")
    b = st.text_input("🔍 Buscar por Nombre de Propietario o Barrio:")
    df_e = df.copy()
    if b:
        df_e = df_e[df_e["nombre_propietario"].astype(str).str.contains(b, case=False) | df_e["barrio_estandar"].astype(str).str.contains(b, case=False)]
    st.dataframe(df_e, use_container_width=True)
