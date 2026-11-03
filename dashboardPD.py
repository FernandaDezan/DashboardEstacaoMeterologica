import streamlit as st #Para dashboard
import pandas as pd 
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import calendar
import re


st.set_page_config(
    page_title="Dashboard Climático", 
    page_icon="🌤️",
    layout="wide"
)



st.markdown("""
<style>
.stApp {background: radial-gradient(ellipse at 12% 15%, #28133e 0%, #101a32 43%, #07162b 100%); color: #f7f5ff;}
.block-container {max-width: 1480px; padding-top: 1.6rem; padding-bottom: 3rem;}
h1, h2, h3 {color: #f7f4ff !important;}
[data-testid="stMetric"] {background: linear-gradient(120deg,#261638,#10283d); border: 1px solid #555184; border-radius: 16px; padding: 14px 18px; min-height: 115px;}
[data-testid="stMetricLabel"] {color: #d6c9ef;}
[data-testid="stMetricValue"] {color: #f9f8ff;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color: #68508c !important;}
.stButton button[kind="secondary"], [data-testid="stRadio"] label {border-radius: 22px;}
div[data-testid="stRadio"] > div {gap: .55rem;}
div[data-testid="stRadio"] label {border: 1px solid #00cce8; padding: 6px 16px; background: #211735;}
div[data-testid="stRadio"] label:has(input:checked) {background: #02c9e9; color: #081529;}
</style>
""", unsafe_allow_html=True)

st.title("🌤️ Estação Meteorológica")
st.markdown("""
Monitoramento e análise das condições climáticas registradas pelos sensores.
""")
st.divider() #Linha separadora


####DADOS 

df = pd.read_csv("BDEstacaoMeterologica.csv", sep=";")

# Padronizar os nomes das colunas
df.columns = df.columns.str.strip()

# Converter a coluna de data
df["Data"] = pd.to_datetime(
    df["Data"],
    dayfirst=True, #escolhe o padrão de data que o dia vem primeiro
    errors="coerce" #Substitui erros por valores nulos, no lugar de interromper o codigo
)

# Limpar e converter temperatura
df["Temperatura"] = (
    df["Temperatura"]
    .str.replace("°C", "", regex=False) # regex=False: remove exatamente o texto °C, sem expressão regular
    .str.strip() # remove espaços; originalmente o CSV contém texto com °C
)

df["Temperatura"] = pd.to_numeric(
    df["Temperatura"],
    errors="coerce"
)

# Limpar e converter umidade
df["Umidade"] = (
    df["Umidade"]
    .str.replace("%", "", regex=False)
    .str.strip() # remove espaços restantes
)

df["Umidade"] = pd.to_numeric(
    df["Umidade"],
    errors="coerce"
)

# Converter pressão e luminosidade para os gráficos complementares.
# A função extrai o número de valores como "1012 hPa" e "1012,5".
def converter_medicao(serie):
    texto = serie.astype("string").str.replace(",", ".", regex=False)
    numeros = texto.str.extract(r"([-+]?\d+(?:\.\d+)?)", expand=False) #resumidamente, deixa so o numero, preservando as casas decimais e seu sinal 
    return pd.to_numeric(numeros, errors="coerce")

#Trabalha em casos de dados nulos ou desconhecidos 
if "Pressão" in df.columns:
    df["Pressão"] = converter_medicao(df["Pressão"])
else:
    df["Pressão"] = float("nan")

if "Luminosidade" in df.columns:
    df["Luminosidade"] = pd.to_numeric(df["Luminosidade"], errors="coerce")
    df.loc[~df["Luminosidade"].isin([0, 1]), "Luminosidade"] = float("nan")
else:
    df["Luminosidade"] = float("nan")

if "Chuva" not in df.columns:
    df["Chuva"] = float("nan")

# Remover somente registros sem data válida
df = df.dropna(subset=["Data"])

# Evitar erro nos filtros se o CSV não tiver nenhuma data válida
if df.empty:
    st.error("O arquivo não contém datas válidas para análise.")
    st.stop()


# CARDS DO TOPO — mostram a última medição disponível de cada variável.
def ultima_medicao(coluna):
    validos = df.dropna(subset=[coluna]).sort_values("Data")
    return None if validos.empty else float(validos.iloc[-1][coluna]) #-1 pega o ultimo valor

ultima_data = df["Data"].max()
ultima_temp = ultima_medicao("Temperatura")
ultima_umidade = ultima_medicao("Umidade")
ultima_pressao = ultima_medicao("Pressão")
ultima_chuva = ultima_medicao("Chuva")

card_data, card_temp, card_umidade, card_pressao, card_chuva = st.columns([1.5, 1, 1, 1, 1])
with card_data:
    st.metric("🗓️ Última medição", ultima_data.strftime("%d/%m/%Y às %H:%M"))
with card_temp:
    st.metric("🌡️ Temperatura", f"{ultima_temp:.1f} °C" if ultima_temp is not None else "Sem dados")
with card_umidade:
    st.metric("💧 Umidade", f"{ultima_umidade:.0f} %" if ultima_umidade is not None else "Sem dados")
with card_pressao:
    st.metric("◉ Pressão", f"{ultima_pressao:.1f} hPa" if ultima_pressao is not None else "Sem dados")
with card_chuva:
    st.metric("🌧️ Chuva", "Sim" if ultima_chuva == 1 else "Não" if ultima_chuva == 0 else "Sem dados")

st.divider()

####Filtro por data 

st.subheader("Temperatura e Umidade")

st.write(
    "Visualize a temperatura e a umidade médias "
    "registradas em cada hora do dia."
)

data_selecionada = st.date_input(  #Cria o calendário interativo no Streamlit.
    "📅 Selecione uma data:",
    value=df["Data"].min().date(), #value define a data inicialmente selecionada.(escolhemos a primeira data do bd)
    min_value=df["Data"].min().date(),
    max_value=df["Data"].max().date(), #mpedem a seleção de datas fora do período do arquivo
    format="DD/MM/YYYY"
)

df_dia = df[
    df["Data"].dt.date == data_selecionada
].dropna(
    subset=["Temperatura", "Umidade"]
).copy()

if df_dia.empty:
    st.warning("Não há medições para a data selecionada.")

else:
    df_dia["Hora"] = df_dia["Data"].dt.hour #dt.hour extrai so as hrs 

    # Calcular a média de cada hora
    df_hora = (
        df_dia.groupby("Hora")
        .agg(
            Temperatura=("Temperatura", "mean"),
            Umidade=("Umidade", "mean")
        )
        .reindex(range(24)) #produz um numero de 0 a 23 (hrs). reindex, informa que tem que ter um valor para cada um desses numeros
        .reset_index() # transforma o índice Hora novamente em coluna
    )

    df_hora["Horario"] = (
        df_hora["Hora"].astype(str).str.zfill(2) + "h" #str.zfill(2): 1 em 01
    )

    ##### Grafico

    fig = make_subplots(
        specs=[[{"secondary_y": True}]] #cria um segundo eixo vertical a direta 
    )

    # Temperatura em colunas
    fig.add_trace(
        go.Bar( #cria colunas 
            x=df_hora["Horario"],
            y=df_hora["Temperatura"],
            name="Temperatura",
            marker_color="#F6AB39",
            hovertemplate="%{y:.2f} °C<extra></extra>" #personaliza valor ao passar o mause no grafico 
        ),
        secondary_y=False
    )

    # Umidade em linha
    fig.add_trace(
        go.Scatter( #Cria linha e seus pontos
            x=df_hora["Horario"],
            y=df_hora["Umidade"],
            name="Umidade",
            mode="lines+markers", #Faz aparecer como linhas com pontos em cada hr
            connectgaps=False, #Não liga trecho de linhas quando haver uma hr sem medição
            line=dict(
                color="#55C6FA",
                width=3
            ),
            marker=dict(size=6),
            hovertemplate="%{y:.2f}%<extra></extra>"
        ),
        secondary_y=True
    )


    # Eixo X: horários
    fig.update_xaxes( #eixo horizontal
        title_text="Horário",
        categoryorder="array",
        categoryarray=[
            f"{hora:02d}h" for hora in range(24) #fica 24 hrs idependente se houver medição ou não
        ],
        tickangle=0 #rotação 
    )

    # Eixo Y esquerdo: temperatura
    fig.update_yaxes(
        title_text="Temperatura (°C)",
        rangemode="tozero", # inclui o zero no eixo Y da temperatura
        secondary_y=False
    )

    # Eixo Y direito: umidade
    fig.update_yaxes(
        title_text="Umidade (%)",
        range=[0, 100],
        secondary_y=True
    )

    # Aparência geral
    fig.update_layout(
        title="Temperatura e umidade por hora",
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=520,
        bargap=0.30, #espaço entre as colunas  
        hovermode="x unified", #Quando você posicionar o mouse sobre determinado horário, verá as informações de temperatura e umidade juntas.
        legend=dict(
            orientation="h", #legenda horizontal (uma do lado da outra)
            y=1.12,
            x=1, # posição horizontal à direita
            xanchor="right" #alinhar a direita do grafico 
        ),
        margin=dict( #bordas externas
            l=30,
            r=30,
            t=85,
            b=40
        )
    )

    st.plotly_chart( #mostra o grafico no dash
        fig,
        width="stretch", #utiliza td largura disponivel
        theme=None #preserva nosso tema (dark)
    )




# ==========================================
# CALENDÁRIO CLIMÁTICO
# ==========================================

st.divider()

st.subheader("📅 Calendário climático")

st.write(
    "Acompanhe os registros de chuva e luminosidade "
    "ao longo do mês. Cada cor representa as condições "
    "detectadas pelos sensores durante aquele dia."
)

# Criar uma cópia dos dados
df_calendario = df[
    ["Data", "Chuva", "Luminosidade"]
].copy()

# Garantir que chuva e luminosidade sejam números
for coluna in ["Chuva", "Luminosidade"]:
    df_calendario[coluna] = pd.to_numeric(
        df_calendario[coluna],
        errors="coerce"
    )

# Manter somente leituras válidas de 0 e 1
for coluna in ["Chuva", "Luminosidade"]:
    df_calendario.loc[
        ~df_calendario[coluna].isin([0, 1]),
        coluna
    ] = float("nan")

# Separar dia e mês
df_calendario["Dia"] = df_calendario["Data"].dt.date
df_calendario["Mes"] = df_calendario["Data"].dt.to_period("M")


# Nomes dos meses em português
nomes_meses = [
    "Janeiro", "Fevereiro", "Março", "Abril",
    "Maio", "Junho", "Julho", "Agosto",
    "Setembro", "Outubro", "Novembro", "Dezembro"
]

# Encontrar os meses existentes no banco
meses_disponiveis = sorted( #Coloca em ordem
    df_calendario["Mes"].dropna().unique()
)

# Criar o filtro
mes_selecionado = st.selectbox( #Cria uma caixa de seleção
    "Selecione o mês:",
    options=meses_disponiveis,
    format_func=lambda mes: ( #lambda é uma maneira curta de criar uma função.
        f"{nomes_meses[mes.month - 1]} de {mes.year}"  #"-1" pq começa no 0, e os meses vão de 1 a 12
    ),
    key="filtro_mes_calendario"
)

# Filtrar as medições do mês
df_mes = df_calendario[
    df_calendario["Mes"] == mes_selecionado
].copy()


# Agrupar chuva e luminosidade de forma independente por dia.
# O max() ignora valores ausentes: um único 1 indica ocorrência no dia.
# Se um sensor não tiver nenhuma leitura válida, o resultado será NaN.
resumo_diario = (
    df_mes.groupby("Dia")
    .agg(
        Chuva=("Chuva", "max"),
        Luminosidade=("Luminosidade", "max"),
        Leituras=("Dia", "size"),
        Leituras_chuva=("Chuva", "count"),
        Leituras_luminosidade=("Luminosidade", "count")
    )
)

# Criar um dicionário para consultar os dias
dados_por_dia = resumo_diario.to_dict( 
    orient="index"
)


# Obter ano e mês selecionados
ano = mes_selecionado.year
numero_mes = mes_selecionado.month

# Criar o calendário começando na segunda-feira
cal = calendar.Calendar(firstweekday=0)

# Separar os dias em semanas
semanas = cal.monthdatescalendar( #devolve as datas organizadas por semanas.
    ano,
    numero_mes
)

# Definir a aparência de cada estado
estilos = {
    (0, 0): ("neutro", "—", "Nenhum detectado"),
    (0, 1): ("sol", "☀", "Luminosidade"),
    (1, 0): ("chuva", "☂", "Chuva"),
    (1, 1): ("ambos", "☀☂", "Chuva e luminosidade")
}


st.markdown("""
<style>
.clima-calendario {
    background: linear-gradient(120deg, #241634, #0e253b);
    border: 1px solid #67538e;
    border-radius: 18px;
    padding: 28px;
    width: 100%;
    box-sizing: border-box;
    font-family: Arial, sans-serif;
}

.clima-cabecalho {
    color: #F8FAFC;
    font-size: 21px;
    font-weight: 700;
    margin-bottom: 20px;
}

.clima-grade {
    display: grid; 
    grid-template-columns: repeat(7, minmax(0, 1fr));
    gap: 12px;
}

.clima-semana {
    color: #94A3B8;
    text-align: center;
    font-size: 12px;
    font-weight: bold;
    padding: 10px 0;
}

.clima-dia {
    min-height: 116px;
    border-radius: 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 5px;
    color: #17212F;
    transition: transform 0.15s ease;
}

.clima-dia:hover {
    transform: translateY(-3px);
}

.clima-numero {
    font-size: 23px;
    font-weight: 700;
}

.clima-icone {
    font-size: 22px;
}

.clima-neutro { background: #94A3B8; }
.clima-sol { background: #FACC15; }
.clima-chuva { background: #60A5FA; }
.clima-ambos { background: #A78BFA; }

.clima-sem-dados {
    background: #334155;
    color: #E2E8F0;
}

.clima-vazio {
    min-height: 116px;
}

@media (max-width: 700px) {
    .clima-calendario { padding: 12px; }
    .clima-grade { gap: 4px; }
    .clima-dia, .clima-vazio { min-height: 65px; }
    .clima-numero { font-size: 13px; }
    .clima-icone { font-size: 12px; }
    .clima-cabecalho { font-size: 17px; }
    .clima-semana { font-size: 10px; }
}
</style>
""", unsafe_allow_html=True)


# Nome do mês
nome_mes = nomes_meses[numero_mes - 1]

# Iniciar o HTML do calendário
html_calendario = (
    '<div class="clima-calendario">'
    '<div class="clima-cabecalho">'
    f'{nome_mes} de {ano}'
    '</div>'
    '<div class="clima-grade">'
)

# Cabeçalho dos dias da semana
for nome in ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]:
    html_calendario += (
        f'<div class="clima-semana">{nome}</div>'
    )

# Percorrer as semanas
for semana in semanas:

    # Percorrer cada dia da semana
    for dia in semana:

        # Dias de outros meses ficam vazios
        if dia.month != numero_mes:
            html_calendario += (
                '<div class="clima-vazio"></div>'
            )
            continue

        # Verificar se existem dados no dia
        registro = dados_por_dia.get(dia)

        # Só classificamos o dia se ambos os sensores tiverem leituras válidas.
        if (registro is None
                or pd.isna(registro["Chuva"])
                or pd.isna(registro["Luminosidade"])):
            classe = "sem-dados"
            icone = "?"
            descricao = "Dados insuficientes para classificar o dia"

        else:
            chuva = int(registro["Chuva"])
            luminosidade = int(registro["Luminosidade"])

            classe, icone, descricao = estilos[
                (chuva, luminosidade)
            ]

            quantidade_chuva = int(registro["Leituras_chuva"])
            quantidade_luz = int(registro["Leituras_luminosidade"])

            descricao += (
                f" | {quantidade_chuva} leituras de chuva"
                f" | {quantidade_luz} leituras de luminosidade"
            )

        # Criar o quadradinho do dia
        html_calendario += (
            f'<div class="clima-dia clima-{classe}" '
            f'title="{descricao}">'
            f'<span class="clima-numero">{dia.day}</span>'
            f'<span class="clima-icone">{icone}</span>'
            '</div>'
        )

# Fechar os elementos HTML
html_calendario += '</div></div>'

# Mostrar o calendário
st.markdown(
    html_calendario,
    unsafe_allow_html=True
)


st.markdown("##### Legenda das condições")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown("🟨 **Luminosidade**")

with col2:
    st.markdown("🟦 **Chuva**")

with col3:
    st.markdown("🟪 **Ambos**")

with col4:
    st.markdown("⬜ **Nenhum**")

with col5:
    st.markdown("⬛ **Sem dados**")

st.caption(
    "As cores representam a ocorrência das condições "
    "em algum momento do dia, não necessariamente "
    "ao mesmo tempo."
)



st.divider()

# Futuras análises — agora com os quatro gráficos individuais.
st.subheader("📊 Análises Complementares")
st.write("Explore a evolução de cada variável ao longo do tempo.")

# Os quatro botões controlam TODOS os gráficos abaixo.
periodo = st.radio( #Radio = botão
    "Período de análise:",
    ["Do dia", "Da semana", "Do mês", "Total"],
    horizontal=True,
    key="periodo_analises"
)

# O filtro de referência muda de acordo com o botão selecionado.
if periodo == "Do dia":
    referencia = st.date_input(
        "Dia para analisar:", 
        value=df["Data"].max().date(), #Data que ira aparecer automaticamente 
        min_value=df["Data"].min().date(), max_value=df["Data"].max().date(), #Data maxima e minima que ele pode selecionar
        format="DD/MM/YYYY", key="dia_analises"
    )
    #Aplica filtro e formata
    df_analises = df[df["Data"].dt.date == referencia].copy()
    df_analises["Eixo"] = df_analises["Data"].dt.hour
    categorias = list(range(24))
    rotulos = [f"{h:02d}h" for h in categorias]
    titulo_eixo = "Horário"

elif periodo == "Da semana":
    referencia = st.date_input(
        "Escolha um dia da semana desejada:", value=df["Data"].max().date(),
        min_value=df["Data"].min().date(), max_value=df["Data"].max().date(),
        format="DD/MM/YYYY", key="semana_analises"
    )
    inicio = pd.Timestamp(referencia) - pd.Timedelta(days=referencia.weekday()) #Pega o dia da semana (retornado em numeor), e subtrai os numeros, chegando na segunda, independete que dia da semana seja
    fim = inicio + pd.Timedelta(days=7)
    st.caption(f"Semana: {inicio:%d/%m/%Y} a {(fim - pd.Timedelta(days=1)):%d/%m/%Y}")
    df_analises = df[(df["Data"] >= inicio) & (df["Data"] < fim)].copy()
    df_analises["Eixo"] = df_analises["Data"].dt.date
    categorias = [(inicio + pd.Timedelta(days=i)).date() for i in range(7)]
    rotulos = [d.strftime("%d/%m") for d in categorias]
    titulo_eixo = "Dia da semana"
elif periodo == "Do mês":
    mes_analise = st.selectbox(
        "Mês para analisar:", options=meses_disponiveis,
        format_func=lambda mes: f"{nomes_meses[mes.month-1]} de {mes.year}",
        index=len(meses_disponiveis)-1, key="mes_analises"
    )
    df_analises = df[df["Data"].dt.to_period("M") == mes_analise].copy()
    df_analises["Eixo"] = df_analises["Data"].dt.day
    categorias = list(range(1, mes_analise.days_in_month+1))
    rotulos = [f"{dia:02d}" for dia in categorias]
    titulo_eixo = "Dia do mês"
else:
    df_analises = df.copy()
    df_analises["Eixo"] = df_analises["Data"].dt.to_period("M")
    categorias = sorted(df_analises["Eixo"].unique())
    rotulos = [str(mes) for mes in categorias]
    titulo_eixo = "Mês"

# Nos períodos maiores, a média é calculada por dia ou por mês.
# Para luminosidade (0 ou 1), a média é a proporção de leituras com luz.
def grafico_individual(coluna, titulo, cor, unidade, tipo="linha"):
    dados = df_analises.groupby("Eixo")[coluna].mean().reindex(categorias)
    fig_individual = go.Figure()
    if tipo == "barra":
        fig_individual.add_trace(go.Bar(
            x=rotulos, y=dados.to_numpy(), name=titulo,
            marker_color=cor, hovertemplate="%{x}: %{y:.2f}<extra></extra>"
        ))
    else:
        fig_individual.add_trace(go.Scatter(
            x=rotulos, y=dados.to_numpy(), name=titulo,
            mode="lines+markers", connectgaps=False,
            line=dict(color=cor, width=3), marker=dict(size=5),
            fill="tozeroy" if coluna == "Umidade" else None,
            hovertemplate="%{x}: %{y:.2f}<extra></extra>"
        ))
    fig_individual.update_layout(
        title=titulo, height=300, template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, margin=dict(l=18, r=15, t=55, b=35),
        xaxis=dict(title=titulo_eixo, type="category", categoryorder="array", categoryarray=rotulos),
        yaxis=dict(title=unidade),
        font=dict(color="#f3edff")
    )
    if coluna == "Luminosidade":
        fig_individual.update_yaxes(range=[0, 1.05])
    if coluna == "Umidade":
        fig_individual.update_yaxes(range=[0, 100])
    return fig_individual

if df_analises.empty:
    st.info("Não existem registros para o período escolhido.")
else:
    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.plotly_chart(grafico_individual("Luminosidade", "☀️ Luminosidade", "#FACC15", "Proporção de leituras (0 a 1)", "barra"), width="stretch", theme=None)
    with col2:
        st.plotly_chart(grafico_individual("Temperatura", "🌡️ Temperatura", "#F6AB39", "Temperatura (°C)"), width="stretch", theme=None)
    col3, col4 = st.columns(2, gap="medium")
    with col3:
        st.plotly_chart(grafico_individual("Umidade", "💧 Umidade", "#00D7F4", "Umidade (%)"), width="stretch", theme=None)
    with col4:
        if df_analises["Pressão"].notna().any():
            st.plotly_chart(grafico_individual("Pressão", "◉ Pressão", "#C17CFF", "Pressão (hPa)"), width="stretch", theme=None)
        else:
            st.info("Não há dados válidos de pressão nesse período.")

st.divider()
st.subheader("🔎 Buscar por dia e horário")
st.write("Consulte as medições originais em um intervalo específico.")

col_busca1, col_busca2, col_busca3 = st.columns(3)
with col_busca1:
    dia_busca = st.date_input("Dia:", value=df["Data"].max().date(),
                             min_value=df["Data"].min().date(), max_value=df["Data"].max().date(),
                             format="DD/MM/YYYY", key="dia_busca")
with col_busca2:
    hora_inicio = st.time_input("Das:", value=pd.Timestamp("00:00").time(), key="hora_inicio")
with col_busca3:
    hora_fim = st.time_input("Até:", value=pd.Timestamp("23:59").time(), key="hora_fim")

if hora_inicio > hora_fim:
    st.warning("O horário inicial deve ser anterior ao horário final.")
else:
    consulta = df[(df["Data"].dt.date == dia_busca) &
                  (df["Data"].dt.time >= hora_inicio) &
                  (df["Data"].dt.time <= hora_fim)]
    if consulta.empty:
        st.info("Nenhuma medição encontrada nesse intervalo.")
    else:
        st.dataframe(consulta[["Data", "Temperatura", "Umidade", "Pressão", "Luminosidade", "Chuva"]].sort_values("Data"),
                     width="stretch", hide_index=True)
