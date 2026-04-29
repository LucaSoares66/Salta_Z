import streamlit as st
import pandas as pd
import boto3
import io
import folium
from streamlit_folium import st_folium
import random
import unicodedata

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

# remove duplicadas
df = df.loc[:, ~df.columns.duplicated()]

# remove sufixos
df = df.rename(columns=lambda x: x.replace("_X", "").replace("_Y", "_REF"))

# -------------------------------
# ENCONTRAR COLUNAS
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

if None in [col_estado, col_lat, col_lon, col_sit]:
    st.error("Colunas essenciais não encontradas")
    st.write(df.columns)
    st.stop()

# -------------------------------
# NORMALIZAÇÃO
# -------------------------------
def normalizar(texto):
    if pd.isna(texto):
        return None
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8')
    return texto

df[col_func] = df[col_func].apply(normalizar)
df[col_sit] = df[col_sit].astype(str).str.strip().str.upper()

# -------------------------------
# LAT/LON
# -------------------------------
df[col_lat] = pd.to_numeric(df[col_lat], errors="coerce")
df[col_lon] = pd.to_numeric(df[col_lon], errors="coerce")

df = df.dropna(subset=[col_lat, col_lon])

df = df[
    (df[col_lat].between(-90, 90)) &
    (df[col_lon].between(-180, 180))
]

# -------------------------------
# FILTRO ESTADOS
# -------------------------------
df = df[~df[col_estado].isin(['AP', 'PA', 'AC'])]

# -------------------------------
# SIDEBAR
# -------------------------------
st.sidebar.header("Filtros")

filtro_func = st.sidebar.selectbox(
    "Funcionando?",
    ["todos", "sim", "nao"]
)

if filtro_func != "todos":
    df = df[df[col_func] == filtro_func]

# -------------------------------
# CORES DINÂMICAS
# -------------------------------
def gerar_cor():
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

situacoes_unicas = df[col_sit].dropna().unique()
cores = {sit: gerar_cor() for sit in situacoes_unicas}

def get_color(situacao):
    return cores.get(situacao, "#000000")

# -------------------------------
# MAPA
# -------------------------------
mapa = folium.Map(
    location=[-14.2350, -51.9253],
    zoom_start=4
)

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
# OUTPUT MAPA
# -------------------------------
st_folium(mapa, use_container_width=True)

# -------------------------------
# LEGENDA FORA DO MAPA
# -------------------------------
st.subheader("Legenda")

cols = st.columns(3)

for i, (sit, cor) in enumerate(cores.items()):
    nome_curto = sit[:60] + "..." if len(sit) > 60 else sit

    with cols[i % 3]:
        st.markdown(
            f"<span style='color:{cor}; font-size:20px;'>●</span> {nome_curto}",
            unsafe_allow_html=True
        )
