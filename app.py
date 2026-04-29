import streamlit as st
import pandas as pd
import boto3
import io
import folium
import random
from streamlit_folium import st_folium

# -------------------------------
# CONFIG
# -------------------------------
st.set_page_config(layout="wide")

# -------------------------------
# HEADER
# -------------------------------
col1, col2 = st.columns([1, 4])

with col1:
    st.image("FUNASA_LOGO.jpeg", width=100)

with col2:
    st.title("Mapa de Unidades SALTA")

# -------------------------------
# FUNÇÃO S3
# -------------------------------
@st.cache_data
def carregar_dados():
    s3 = boto3.client(
        "s3",
        aws_access_key_id=st.secrets["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=st.secrets["AWS_SECRET_ACCESS_KEY"],
        region_name=st.secrets["AWS_DEFAULT_REGION"]
    )

    obj = s3.get_object(
        Bucket=st.secrets["BUCKET_NAME"],
        Key=st.secrets["FILE_KEY"]
    )

    df = pd.read_excel(io.BytesIO(obj["Body"].read()))
    return df

# -------------------------------
# LOAD
# -------------------------------
df = carregar_dados()

# -------------------------------
# LIMPEZA DE COLUNAS
# -------------------------------
df.columns = (
    df.columns
    .str.strip()
    .str.upper()
    .str.normalize('NFKD')
    .str.encode('ascii', errors='ignore')
    .str.decode('utf-8')
)

df = df.loc[:, ~df.columns.duplicated()]
df = df.rename(columns=lambda x: x.replace("_X", "").replace("_Y", "_REF"))

# -------------------------------
# DETECTAR COLUNAS
# -------------------------------
def encontrar_coluna(df, nomes):
    for col in df.columns:
        for nome in nomes:
            if nome in col:
                return col
    return None

col_estado = encontrar_coluna(df, ["ESTADO", "UF"])
col_lat = encontrar_coluna(df, ["LAT"])
col_lon = encontrar_coluna(df, ["LON"])
col_func = encontrar_coluna(df, ["FUNCIONANDO"])
col_sit = encontrar_coluna(df, ["SITUACAO"])

# -------------------------------
# TRATAMENTO
# -------------------------------
df[col_func] = df[col_func].astype(str).str.lower()
df[col_sit] = df[col_sit].astype(str).str.strip()

df[col_lat] = pd.to_numeric(df[col_lat], errors="coerce")
df[col_lon] = pd.to_numeric(df[col_lon], errors="coerce")

df = df.dropna(subset=[col_lat, col_lon])

df = df[
    (df[col_lat].between(-90, 90)) &
    (df[col_lon].between(-180, 180))
]

# -------------------------------
# FILTRO
# -------------------------------
df = df[~df[col_estado].isin(['AP', 'PA', 'AC'])]

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.header("Filtros")

filtro_func = st.sidebar.selectbox(
    "Funcionando?",
    ["todos", "sim", "não"]
)

if filtro_func != "todos":
    df = df[df[col_func] == filtro_func]

# -------------------------------
# CORES FIXAS (IMPORTANTE)
# -------------------------------
situacoes = sorted(df[col_sit].dropna().unique())

if "cores_mapa" not in st.session_state:
    cores = {}
    for sit in situacoes:
        cores[sit] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    st.session_state.cores_mapa = cores

cores = st.session_state.cores_mapa

def get_color(situacao):
    return cores.get(situacao, "#999999")

# -------------------------------
# MAPA
# -------------------------------
mapa = folium.Map(location=[-14.2350, -51.9253], zoom_start=4)

# -------------------------------
# MARCADORES
# -------------------------------
for lat, lon, estado, sit, func in zip(
    df[col_lat],
    df[col_lon],
    df[col_estado],
    df[col_sit],
    df[col_func]
):
    folium.CircleMarker(
        location=[lat, lon],
        radius=5,
        color=get_color(sit),
        fill=True,
        fill_opacity=0.7,
        popup=f"""
        <b>Estado:</b> {estado}<br>
        <b>Situação:</b> {sit}<br>
        <b>Funcionando:</b> {func}
        """
    ).add_to(mapa)

# -------------------------------
# MOSTRAR MAPA
# -------------------------------
st_folium(mapa, use_container_width=True)

# -------------------------------
# LEGENDA FORA DO MAPA
# -------------------------------
st.markdown("### Legenda")

for sit, cor in cores.items():
    nome = sit

    # simplificar texto longo
    if "não está em operação" in sit.lower():
        nome = "Sistema não está em operação"

    st.markdown(
        f"<span style='color:{cor}; font-size:18px;'>●</span> {nome}",
        unsafe_allow_html=True
    )
