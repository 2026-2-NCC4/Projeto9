"""CTI — Plataforma analítica de planejamento financeiro (concessão sem setor declarado)."""
from pathlib import Path
import sys
import os
import hmac
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Permite importar os módulos do Backend mantendo Frontend/Backend separados.
BACKEND = Path(__file__).resolve().parents[1] / 'Backend'
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from core.analise import (
    COMPONENTES, NOMES_METRICAS, alertas, conferir_caixa,
    fluxo_caixa_componentes, formatar_moeda, formatar_percentual,
    indices_dfc, media_cenarios, regressao_temporal, resumo_executivo,
)
from core.contabilidade import (
    carregar_planilha_convertida, agregar_por_ano, formatar_kpi,
    ano_mais_recente_com_liquidez,
)
from ui_contabilidade import mostrar_painel

RAIZ = BACKEND
BASE = RAIZ / 'dados' / 'indicadores_cti.csv'
COR_AZUL = '#69A9FF'
COR_VERMELHO = '#F0717D'
COR_VERDE = '#39C7AE'
COR_CINZA = '#A8B8CA'
COR_TURQUESA = '#39C7AE'

st.set_page_config(
    page_title='CTI | Inteligência Financeira', page_icon='📊', layout='wide',
    initial_sidebar_state='expanded',
)

# Identidade visual provisória CTI — tema premium escuro.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root {
  --cti-bg: #07111F;
  --cti-sidebar: #081625;
  --cti-surface: #101F31;
  --cti-surface-2: #14263A;
  --cti-border: #263B52;
  --cti-text: #EDF3FA;
  --cti-muted: #9FB0C3;
  --cti-accent: #39C7AE;
  --cti-blue: #69A9FF;
}
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
.stApp, [data-testid="stAppViewContainer"] {
  background: radial-gradient(ellipse at 82% 0%, rgba(45, 104, 142, .18), transparent 32%), var(--cti-bg);
  color: var(--cti-text);
}
[data-testid="stHeader"] { background: rgba(7,17,31,.78); }
[data-testid="stMainBlockContainer"] { max-width: 1500px; padding-top: 1.55rem; padding-bottom: 3rem; }
[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
[data-testid="stMain"] h4 { color: #F4F7FB !important; letter-spacing: -.025em; }
[data-testid="stMain"] h1 { font-weight: 750; }
[data-testid="stMain"] p, [data-testid="stMain"] li { color: #C2CFDD; }
[data-testid="stMain"] [data-testid="stCaptionContainer"] p { color: #8FA2B8 !important; }
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] { color: #B7C5D5 !important; }
[data-testid="stMetric"] {
  background: linear-gradient(145deg, #14263A 0%, #101E2F 100%);
  border: 1px solid #263B52; border-radius: 16px; padding: 16px 18px;
  box-shadow: 0 12px 30px rgba(0,0,0,.14); min-height: 112px;
}
[data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] { color: #9FB2C7 !important; font-size: .82rem; font-weight: 550; }
[data-testid="stMetricValue"], [data-testid="stMetricValue"] div { color: #F4F7FB !important; font-weight: 750; letter-spacing: -.035em; }
[data-testid="stMetricDelta"] { font-size: .78rem; }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0A1A2B 0%, #081523 100%);
  border-right: 1px solid #1C3045;
}
[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #DCE6F0 !important; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #91A5BA !important; }
[data-testid="stSidebar"] hr { border-color: #263B52; }
[data-testid="stSidebar"] [data-testid="stRadio"] > label { display:none; }
[data-testid="stSidebar"] div[role="radiogroup"] { gap: .28rem; }
[data-testid="stSidebar"] div[role="radiogroup"] label {
  border: 1px solid transparent; border-radius: 10px; padding: .58rem .65rem;
  transition: background .15s ease, border-color .15s ease;
}
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
  background: #153447; border-color: #28546A; box-shadow: inset 3px 0 0 #39C7AE;
}
[data-testid="stSidebar"] div[role="radiogroup"] label p { color: #DCE6F0 !important; font-weight: 550; }
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p { color: #FFFFFF !important; font-weight: 700; }
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div { background: #102237; border-color: #2B4158; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] * { color: #EAF1F8 !important; }
[data-testid="stMain"] [data-baseweb="select"] > div,
[data-testid="stMain"] [data-baseweb="input"] > div,
[data-testid="stMain"] textarea { background: #102237; border-color: #2B4158; color: #EDF3FA; }
[data-testid="stMain"] input { color: #EDF3FA !important; }
[data-testid="stMain"] [data-baseweb="select"] * { color: #EDF3FA; }
[data-testid="stButton"] button, [data-testid="stFormSubmitButton"] button {
  border-radius: 10px; border: 1px solid #31516C; background: #18364F;
  color: #F4F8FC; font-weight: 650; transition: all .16s ease;
}
[data-testid="stButton"] button:hover, [data-testid="stFormSubmitButton"] button:hover {
  border-color: #39C7AE; background: #204A5B; color: #FFFFFF;
}
[data-testid="stDownloadButton"] button { border-radius: 10px; }
[data-testid="stAlert"] { border-radius: 12px; border: 1px solid #30465D; background: #12243A; }
[data-testid="stExpander"] { border: 1px solid #263B52; border-radius: 12px; background: #0E1C2C; }
[data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid #263B52; border-radius: 12px; overflow: hidden; }
hr { border-color: #263B52 !important; }
.cti-brand { display:flex; align-items:center; gap:12px; padding: 7px 4px 17px; }
.cti-mark { width:43px; height:43px; border-radius:13px; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(145deg,#39C7AE,#247D91); color:#061522; font-weight:850; letter-spacing:-.06em; font-size:1.05rem;
  box-shadow:0 8px 22px rgba(57,199,174,.18); }
.cti-brand-name { color:#F3F7FB; font-size:1.02rem; font-weight:750; line-height:1.15; }
.cti-brand-sub { color:#8FA6BD; font-size:.62rem; letter-spacing:.15em; font-weight:650; margin-top:4px; }
.page-eyebrow { color:#70BDB6; font-size:.68rem; letter-spacing:.16em; font-weight:750; text-transform:uppercase; margin-bottom:5px; }
.context-pill { display:inline-block; border:1px solid #29435B; background:#102237; border-radius:999px; padding:6px 11px; color:#B7C8D9; font-size:.76rem; }
.login-hero { min-height: 570px; padding: 42px; border-radius: 24px; border:1px solid #254158;
  background: radial-gradient(circle at 80% 20%, rgba(57,199,174,.20), transparent 28%),
              radial-gradient(circle at 15% 90%, rgba(73,134,204,.18), transparent 32%),
              linear-gradient(145deg,#102B43 0%,#0A1A2B 58%,#091624 100%);
  display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 25px 70px rgba(0,0,0,.22); }
.login-brand { display:flex; align-items:center; gap:14px; }
.login-mark { width:58px; height:58px; border-radius:17px; display:flex; align-items:center; justify-content:center;
  background:linear-gradient(145deg,#45D4B8,#2B8398); color:#061522; font-size:1.45rem; font-weight:850; letter-spacing:-.08em; }
.login-brand strong { display:block; color:#F2F7FB; font-size:1.03rem; letter-spacing:.02em; }
.login-brand small { display:block; color:#8FAFC2; font-size:.62rem; letter-spacing:.19em; margin-top:4px; }
.login-kicker { color:#65CDBD; font-size:.68rem; font-weight:750; letter-spacing:.18em; text-transform:uppercase; }
.login-hero h1 { color:#F4F8FC; font-size:clamp(2.2rem,4vw,3.5rem); line-height:1.04; letter-spacing:-.055em; max-width:560px; margin:15px 0; }
.login-hero p { color:#B2C4D5; font-size:1rem; line-height:1.7; max-width:480px; }
.login-chart { margin-top:28px; padding:18px; border:1px solid rgba(150,190,210,.17); border-radius:16px; background:rgba(7,19,32,.35); }
.login-chart-label { color:#8FAFC2; font-size:.62rem; letter-spacing:.15em; font-weight:700; }
.login-foot { color:#7892A9; font-size:.68rem; letter-spacing:.08em; }
[data-testid="stVerticalBlockBorderWrapper"] { background:linear-gradient(160deg,#14263A,#0E1C2C); border:1px solid #2B4057; border-radius:22px; padding:24px; box-shadow:0 22px 60px rgba(0,0,0,.16); }
.login-card { background:linear-gradient(160deg,#14263A,#0E1C2C); border:1px solid #2B4057; border-radius:22px; padding:30px; box-shadow:0 22px 60px rgba(0,0,0,.20); }
.login-card h2 { color:#F4F7FB; font-size:1.7rem; letter-spacing:-.04em; }
.login-card p { color:#9FB1C4; }
.login-note { color:#8EA3B8; font-size:.72rem; line-height:1.55; }
@media (max-width: 900px) { .login-hero { min-height:420px; padding:28px; } .login-card { padding:22px; } }
</style>
""", unsafe_allow_html=True)

def ler_configuracao_acesso():
    """Lê credenciais de secrets/env; não mantém senhas no código-fonte."""
    usuario = os.getenv('CTI_USER', '').strip()
    senha = os.getenv('CTI_PASSWORD', '')
    permitir_demo = os.getenv('CTI_ENABLE_DEMO', 'false').strip().lower() in {'1', 'true', 'yes', 'sim'}
    try:
        auth = st.secrets.get('auth', {})
        usuario = usuario or str(auth.get('username', '')).strip()
        senha = senha or str(auth.get('password', ''))
        if 'allow_demo' in auth:
            permitir_demo = str(auth.get('allow_demo')).strip().lower() in {'1', 'true', 'yes', 'sim'}
    except Exception:
        pass
    return usuario, senha, permitir_demo


def tela_login():
    """Tela de entrada. O modo demo é explicitamente identificado e não é autenticação corporativa."""
    usuario_config, senha_config, permitir_demo = ler_configuracao_acesso()
    col_hero, col_login = st.columns([1.12, .88], gap='large')
    with col_hero:
        st.markdown("""
        <div class="login-hero">
          <div class="login-brand">
            <div class="login-mark">CTI</div>
            <div><strong>INTELIGÊNCIA FINANCEIRA</strong><small>PLATAFORMA ANALÍTICA</small></div>
          </div>
          <div>
            <div class="login-kicker">ANÁLISE • CENÁRIOS • DECISÕES</div>
            <h1>Transforme dados em decisões.</h1>
            <p>Uma visão integrada dos indicadores financeiros da concessão, com comparação de cenários, análise de caixa e simulações para apoiar decisões.</p>
            <div class="login-chart">
              <div class="login-chart-label">VISÃO FINANCEIRA • 12 ANOS SIMULADOS</div>
              <svg viewBox="0 0 520 118" width="100%" role="img" aria-label="Ilustração abstrata de evolução financeira">
                <defs><linearGradient id="ctiLine" x1="0" x2="1"><stop offset="0" stop-color="#69A9FF"/><stop offset="1" stop-color="#39C7AE"/></linearGradient></defs>
                <g stroke="#FFFFFF" stroke-opacity=".10" stroke-width="1"><path d="M0 25H520M0 58H520M0 91H520"/></g>
                <path d="M8 91 C55 83 70 88 108 72 S174 76 210 58 S275 65 312 43 S378 49 412 29 S474 31 512 12" fill="none" stroke="url(#ctiLine)" stroke-width="4" stroke-linecap="round"/>
                <path d="M8 91 C55 83 70 88 108 72 S174 76 210 58 S275 65 312 43 S378 49 412 29 S474 31 512 12 L512 112 L8 112Z" fill="#39C7AE" fill-opacity=".07"/>
                <circle cx="512" cy="12" r="5" fill="#39C7AE"/>
              </svg>
            </div>
          </div>
          <div class="login-foot">AMBIENTE DE ANÁLISE FINANCEIRA • CTI / FECAP</div>
        </div>
        """, unsafe_allow_html=True)
    with col_login:
        with st.container(border=True):
            st.markdown('## Acesse sua plataforma')
            st.markdown('Entre com suas credenciais para visualizar os indicadores e análises.')
            with st.form('form_login', clear_on_submit=False):
                email = st.text_input('Usuário ou e-mail', placeholder='Digite seu usuário')
                senha = st.text_input('Senha', type='password', placeholder='Digite sua senha')
                entrar = st.form_submit_button('Entrar na plataforma', use_container_width=True)
            if entrar:
                if usuario_config and senha_config and hmac.compare_digest(email.strip(), usuario_config) and hmac.compare_digest(senha, senha_config):
                    st.session_state['cti_autenticado'] = True
                    st.session_state['cti_modo_acesso'] = 'Acesso configurado'
                    st.session_state['cti_usuario'] = email.strip()
                    st.rerun()
                elif not usuario_config or not senha_config:
                    st.error('O acesso com usuário e senha ainda não foi configurado. Configure .streamlit/secrets.toml ou use a demonstração local, se habilitada.')
                else:
                    st.error('Usuário ou senha inválidos.')
            if permitir_demo:
                st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
                if st.button('Acessar demonstração', use_container_width=True, type='secondary'):
                    st.session_state['cti_autenticado'] = True
                    st.session_state['cti_modo_acesso'] = 'Demonstração local'
                    st.session_state['cti_usuario'] = 'Visitante'
                    st.rerun()
                st.markdown('<div class="login-note">Modo demonstrativo: permite visualizar a interface sem autenticação corporativa. Não utilize esta opção em uma publicação com dados confidenciais.</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="login-note">Acesso restrito. Para habilitar o login, configure as credenciais do ambiente. O modo de demonstração está desativado.</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-note" style="text-align:center;margin-top:16px">CTI • INTELIGÊNCIA FINANCEIRA<br/>Ambiente de análise de dados simulados</div>', unsafe_allow_html=True)


if not st.session_state.get('cti_autenticado', False):
    tela_login()
    st.stop()

@st.cache_data(show_spinner='Lendo indicadores financeiros...')
def carregar_base():
    data = pd.read_csv(BASE, encoding='utf-8-sig')
    if data.duplicated(['ano', 'cenario']).any():
        raise ValueError('A base tem pares ano/cenário duplicados.')
    return data


def grafico_estilo(fig, altura=370):
    fig.update_layout(
        template='plotly_dark', height=altura,
        margin=dict(t=42, r=18, b=24, l=18),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, Segoe UI, sans-serif', color='#C7D4E2', size=12),
        legend_title_text='', hovermode='x unified',
        title_font=dict(color='#EDF3FA', size=15),
        hoverlabel=dict(bgcolor='#14263A', bordercolor='#38536D', font_color='#F4F7FB'),
    )
    fig.update_xaxes(showgrid=False, color='#9FB1C4', linecolor='#2B4057', tickfont=dict(color='#9FB1C4'))
    fig.update_yaxes(gridcolor='#24384D', zerolinecolor='#50657B', color='#9FB1C4', tickfont=dict(color='#9FB1C4'))
    return fig


def bilhoes(tabela, colunas):
    convertido = tabela.copy()
    for c in colunas:
        convertido[c] = convertido[c] / 1e9
    return convertido


def exibir_alerta(nivel, titulo, detalhe):
    if nivel in ('atenção', 'qualidade'):
        st.warning(f'**{titulo}** — {detalhe}', icon='⚠️')
    elif nivel == 'meta':
        st.info(f'**{titulo}** — {detalhe}', icon='🎯')
    else:
        st.info(f'**{titulo}** — {detalhe}', icon='ℹ️')


def exibir_metricas(linha):
    metricas = [
        ('Receita da DRE (bruta)', 'receita', False),
        ('Resultado operacional', 'resultado_operacional', False),
        ('Lucro líquido', 'lucro_liquido', False),
        ('Margem operacional / receita bruta', 'margem_operacional_pct', True),
        ('EBITDA (original)', 'ebitda', False),
        ('Geração líquida de caixa', 'geracao_caixa', False),
        ('Saldo final de caixa', 'saldo_final_caixa', False),
        ('Ativo total', 'ativo_total', False),
    ]
    for i in (0, 4):
        cols = st.columns(4)
        for col, (nome, campo, pct) in zip(cols, metricas[i:i + 4]):
            col.metric(nome, formatar_percentual(linha[campo]) if pct else formatar_moeda(linha[campo]))


try:
    df = carregar_base()
    df_contabilidade = carregar_planilha_convertida()
    if not set(zip(df_contabilidade.cenario, df_contabilidade.ano)) == set(zip(df.cenario, df.ano)):
        raise ValueError('As duas bases não possuem os mesmos pares ano/cenário.')
except (FileNotFoundError, ValueError) as erro:
    st.error(f'Não foi possível carregar as bases financeiras: {erro}. Execute os scripts de preparação e importação da planilha.')
    st.stop()

lista_cenarios = sorted(df['cenario'].unique().tolist())
lista_anos = sorted(df['ano'].unique().tolist())

with st.sidebar:
    st.markdown('''
    <div class="cti-brand">
      <div class="cti-mark">CTI</div>
      <div><div class="cti-brand-name">Inteligência<br/>Financeira</div><div class="cti-brand-sub">PLATAFORMA ANALÍTICA</div></div>
    </div>
    ''', unsafe_allow_html=True)
    st.markdown('<div class="page-eyebrow">PAINEL DE CONTROLE</div>', unsafe_allow_html=True)
    opcoes_secao = {
        'Visão executiva': '◈  Visão geral',
        'Contabilidade e Finanças': '▦  Contabilidade e Finanças',
        'Fluxo de caixa': '↗  Fluxo de caixa',
        'Comparar cenários': '⇄  Comparar cenários',
        'Simulador': '⌁  Simulador financeiro',
        'Regressão': '⌗  Análises estatísticas',
        'Qualidade e fontes': '✓  Dados e metodologia',
    }
    secao = st.radio(
        'Navegação', list(opcoes_secao),
        format_func=lambda valor: opcoes_secao[valor],
        label_visibility='collapsed', key='secao_dashboard',
    )
    st.divider()
    st.markdown('<div class="page-eyebrow">FILTROS DA ANÁLISE</div>', unsafe_allow_html=True)
    modo = st.radio('Análise principal', ['Cenário individual', 'Média simples de cenários'],
                    help='Cenários são alternativas simuladas, não unidades de negócio somáveis.')
    if modo == 'Cenário individual':
        escolhido = st.selectbox('Cenário', lista_cenarios,
                                 format_func=lambda c: f'Cenário {c:05d}')
        cenarios_selecionados = [escolhido]
        titulo_recorte = f'Cenário {escolhido:05d}'
    else:
        cenarios_selecionados = st.multiselect('Cenários para a média', lista_cenarios,
                                                default=lista_cenarios[:3],
                                                format_func=lambda c: f'Cenário {c:05d}',
                                                help='Média aritmética de valores financeiros; margens calculadas sobre os valores médios.')
        titulo_recorte = f'Média simples de {len(cenarios_selecionados)} cenários'
    intervalo = st.slider('Anos simulados', min(lista_anos), max(lista_anos),
                          (min(lista_anos), max(lista_anos)))
    st.divider()
    with st.expander('Preferências e metas de análise', expanded=False):
        meta = st.slider(
            'Referência de margem operacional (%)', 0, 100, 20, 5,
            help=('Alvo exploratório para os avisos do painel. '
                  'Não é uma meta oficial da CTI e não modifica os dados.')
        )
        st.caption('Valor ilustrativo configurável, sem vínculo com meta institucional.')
    st.markdown('<div class="login-note">DADOS SIMULADOS • 12 ANOS<br/>R$ COMO CONVENÇÃO DE APRESENTAÇÃO</div>', unsafe_allow_html=True)
    st.divider()
    st.caption(f'Acesso: {st.session_state.get("cti_modo_acesso", "Sessão") }')
    if st.button('Sair da plataforma', use_container_width=True):
        for chave in ['cti_autenticado', 'cti_modo_acesso', 'cti_usuario']:
            st.session_state.pop(chave, None)
        st.rerun()

if not cenarios_selecionados:
    st.info('Selecione pelo menos um cenário no painel lateral.')
    st.stop()

sub = df[df['cenario'].isin(cenarios_selecionados) & df['ano'].between(*intervalo)].copy()
por_ano = media_cenarios(sub)
sub_contabilidade = df_contabilidade[
    df_contabilidade['cenario'].isin(cenarios_selecionados)
    & df_contabilidade['ano'].between(*intervalo)
]
por_ano_contabilidade = agregar_por_ano(
    sub_contabilidade, float(st.session_state.get('cti_wacc', 10.5)) / 100
)
cabecalho_esq, cabecalho_dir = st.columns([2.2, 1])
with cabecalho_esq:
    st.markdown('<div class="page-eyebrow">CTI / INTELIGÊNCIA FINANCEIRA</div>', unsafe_allow_html=True)
    st.title('Visão financeira da concessão' if secao == 'Visão executiva' else opcoes_secao[secao].split('  ', 1)[1])
    st.caption('Análise de desempenho, fluxo de caixa e cenários simulados')
# Por padrão, usar o último ano com balanço completo.
# O Ano 12 não tem passivo circulante ajustado na planilha e, portanto,
# seus seis índices de liquidez não podem ser apresentados.
anos_selecionaveis = por_ano['ano'].tolist()
anos_liquidez = set(por_ano_contabilidade.loc[
    por_ano_contabilidade[['lc', 'ls', 'li', 'lg', 'ccl', 'icc']].notna().all(axis=1), 'ano'
].tolist())
ano_padrao = ano_mais_recente_com_liquidez(por_ano_contabilidade)
if st.session_state.get('cti_periodo_analise') not in anos_selecionaveis:
    st.session_state['cti_periodo_analise'] = ano_padrao
with cabecalho_dir:
    ano_atual = st.selectbox(
        'Período em análise', anos_selecionaveis, key='cti_periodo_analise',
        format_func=lambda ano: (f'Ano simulado {ano}' if ano in anos_liquidez
                                 else f'Ano simulado {ano} · liquidez indisponível'),
        help='O Ano 12 não possui balanço completo na planilha. Os índices de liquidez são calculáveis até o Ano 11.',
    )
linha = por_ano.loc[por_ano['ano'] == ano_atual].iloc[0]
linha_contabilidade = por_ano_contabilidade.loc[por_ano_contabilidade['ano'] == ano_atual].iloc[0]
st.markdown(f'<div class="context-pill">{titulo_recorte} &nbsp; • &nbsp; Ano {ano_atual}</div>', unsafe_allow_html=True)
st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
if ano_atual not in anos_liquidez and secao in ('Visão executiva', 'Contabilidade e Finanças'):
    orientacao_liquidez = (
        f'Selecione o **Ano {max(anos_liquidez)}** para visualizar o último balanço completo.'
        if anos_liquidez else
        'Amplie o filtro **Anos simulados** para incluir o Ano 11, que possui o último balanço completo.'
    )
    st.warning(
        f'**Liquidez indisponível no Ano {ano_atual}.** A planilha original não apresenta o '
        'Passivo Circulante Ajustado neste período. Por isso, os seis índices de liquidez '
        f'não podem ser calculados. {orientacao_liquidez} '
        'Não substituímos valores ausentes por zero ou por dados de outro ano.'
    )
if secao != 'Contabilidade e Finanças':
    exibir_metricas(linha)

if secao == 'Visão executiva':
    st.subheader('O que os resultados mostram?')
    for nivel, titulo, detalhe in alertas(linha, meta):
        exibir_alerta(nivel, titulo, detalhe)
    st.caption('Alertas descritivos gerados por regras auditáveis. Não são recomendações de investimento nem conclusões sobre a viabilidade da concessão.')

    p1, p2 = st.columns([1.5, 1])
    with p1:
        linha_g = bilhoes(por_ano, ['receita', 'resultado_operacional', 'lucro_liquido'])
        longo = linha_g.melt(id_vars='ano', value_vars=['receita', 'resultado_operacional', 'lucro_liquido'],
                             var_name='Indicador', value_name='R$ bilhões')
        longo['Indicador'] = longo['Indicador'].map({
            'receita':'Receita', 'resultado_operacional':'Resultado operacional', 'lucro_liquido':'Lucro líquido'})
        fig = px.line(longo, x='ano', y='R$ bilhões', color='Indicador', markers=True,
                      title='Evolução da DRE por ano simulado', color_discrete_sequence=[COR_AZUL, COR_VERMELHO, COR_VERDE])
        st.plotly_chart(grafico_estilo(fig), use_container_width=True)
    with p2:
        linha_g = bilhoes(por_ano, ['geracao_caixa', 'saldo_final_caixa'])
        longo = linha_g.melt(id_vars='ano', value_vars=['geracao_caixa','saldo_final_caixa'],
                             var_name='Indicador', value_name='R$ bilhões')
        longo['Indicador'] = longo['Indicador'].map({'geracao_caixa':'Geração de caixa',
                                                     'saldo_final_caixa':'Saldo final de caixa'})
        fig = px.bar(longo, x='ano', y='R$ bilhões', color='Indicador', barmode='group',
                     title='Geração versus saldo de caixa',
                     color_discrete_sequence=[COR_VERMELHO, COR_AZUL])
        st.plotly_chart(grafico_estilo(fig), use_container_width=True)
    contagem_ano = df[df['ano'] == ano_atual]
    negativos = int((contagem_ano['geracao_caixa'] < 0).sum())
    st.caption(f'**Contexto:** {negativos:,} de {len(contagem_ano):,} cenários apresentam geração líquida de caixa negativa no Ano {ano_atual}. '
               'Cenários não possuem probabilidades confirmadas, então a frequência não é risco probabilístico.')
    st.info('**Como ler:** lucro vem da DRE; caixa vem da demonstração de fluxo de caixa. Um resultado positivo em um não implica resultado positivo no outro.')

    st.markdown('<div class="page-eyebrow" style="margin-top:28px">LEITURA RÁPIDA DOS INDICADORES</div>', unsafe_allow_html=True)
    st.caption('Indicadores de caixa e liquidez ajustados conforme o dicionário financeiro da planilha.')
    dfc_resumo = indices_dfc(linha)
    giro_resumo = {
        'Liquidez corrente': linha_contabilidade['lc'],
        'Liquidez seca': linha_contabilidade['ls'],
        'Capital de giro líquido': linha_contabilidade['ccl'],
    }
    componentes_resumo = fluxo_caixa_componentes(linha).copy()
    componentes_resumo['R$ bilhões'] = componentes_resumo['Valor'] / 1e9
    r1, r2, r3 = st.columns(3, gap='medium')
    with r1:
        with st.container(border=True):
            st.markdown('#### Eficiência do caixa')
            st.caption('Eficiência e pressão do caixa')
            a, b = st.columns(2)
            a.metric('Geração / receita', formatar_percentual(dfc_resumo['Geração de caixa / Receita']))
            b.metric('Investimentos / receita', formatar_percentual(dfc_resumo['Investimentos / Receita']))
            st.caption(f'Saldo final / receita: **{formatar_percentual(dfc_resumo["Saldo final / Receita"])}**')
    with r2:
        with st.container(border=True):
            st.markdown('#### Liquidez e capital de giro')
            st.caption('Liquidez dos saldos circulantes')
            a, b = st.columns(2)
            a.metric('Liquidez corrente', formatar_kpi(giro_resumo['Liquidez corrente'], 'x'))
            b.metric('Liquidez seca', formatar_kpi(giro_resumo['Liquidez seca'], 'x'))
            st.caption(f'Capital de giro líquido: **{formatar_moeda(giro_resumo["Capital de giro líquido"])}**')
    with r3:
        with st.container(border=True):
            st.markdown('#### Fluxo de caixa')
            st.caption('Ponte resumida do período')
            a, b = st.columns(2)
            a.metric('Saldo inicial', formatar_moeda(linha.saldo_inicial_caixa))
            b.metric('Saldo final', formatar_moeda(linha.saldo_final_caixa))
            st.metric('Geração líquida', formatar_moeda(linha.geracao_caixa))
    fig_resumo = px.bar(componentes_resumo, x='R$ bilhões', y='Componente', orientation='h', color='Valor',
                        color_continuous_scale=[COR_VERMELHO, COR_VERDE], title='Composição resumida do fluxo de caixa')
    st.plotly_chart(grafico_estilo(fig_resumo, 305), use_container_width=True)

elif secao in ('Fluxo de caixa', 'Caixa explicado'):
    st.subheader('Como o caixa do período se formou?')
    st.caption('Cada barra é uma conta original de FLU. O resultado financeiro é mostrado líquido para evitar contar suas entradas e despesas duas vezes.')
    c1, c2, c3 = st.columns(3)
    c1.metric('Saldo no início', formatar_moeda(linha.saldo_inicial_caixa))
    c2.metric('Variação líquida', formatar_moeda(linha.geracao_caixa))
    c3.metric('Saldo no fim', formatar_moeda(linha.saldo_final_caixa))

    componentes = fluxo_caixa_componentes(linha)
    fig = go.Figure(go.Waterfall(
        name='Caixa', orientation='v',
        measure=['absolute'] + ['relative'] * len(componentes) + ['total'],
        x=['Saldo inicial'] + componentes['Componente'].tolist() + ['Saldo final'],
        y=[linha.saldo_inicial_caixa / 1e9] + (componentes['Valor'] / 1e9).tolist() + [linha.saldo_final_caixa / 1e9],
        connector={'line': {'color': '#647D95', 'width': 1}},
        increasing={'marker': {'color': COR_VERDE}},
        decreasing={'marker': {'color': COR_VERMELHO}},
        totals={'marker': {'color': COR_AZUL}},
        hovertemplate='%{x}<br>%{y:,.3f} bilhões de R$<extra></extra>',
    ))
    fig.update_layout(title='Ponte do saldo inicial ao saldo final (R$ bilhões)', yaxis_title='R$ bilhões',
                      xaxis={'tickangle':-32}, showlegend=False)
    st.plotly_chart(grafico_estilo(fig, 495), use_container_width=True)
    conferido = conferir_caixa(linha)
    if conferido['ok']:
        st.success('Reconciliação aprovada: a soma das parcelas coincide com a geração líquida; saldo inicial + geração coincide com saldo final (tolerância R$ 0,01).')
    else:
        st.error('As parcelas não reconciliam com o saldo apresentado. Não utilizar o resultado sem revisar a base.')
    with st.expander('Conferência e composição do fluxo de caixa', expanded=False):
        tab_comp = componentes.copy()
        tab_comp['Valor (R$)'] = tab_comp['Valor'].map(lambda v: f'{v:,.2f}'.replace(',', 'T').replace('.', ',').replace('T', '.'))
        st.dataframe(tab_comp[['Componente', 'Valor (R$)']], hide_index=True, use_container_width=True)
        st.write(f'**Diferença componentes − geração:** {formatar_moeda(conferido["diferenca_componentes"])}')
        st.write(f'**Diferença saldo inicial + geração − saldo final:** {formatar_moeda(conferido["diferenca_saldo"])}')
        st.caption('As diferenças são calculadas antes do arredondamento para a exibição. O FLU foi preservado com os sinais originais.')
    saidas = componentes[componentes['Valor'] < 0].sort_values('Valor')
    if not saidas.empty:
        maior_saida = saidas.iloc[0]
        st.info(f'**Maior saída registrada neste recorte:** {maior_saida["Componente"]}, '
                f'{formatar_moeda(maior_saida["Valor"])}. Isso descreve sua magnitude; não determina, isoladamente, o motivo do resultado.')

elif secao == 'Contabilidade e Finanças':
    mostrar_painel(
        df_contabilidade, cenarios_selecionados, intervalo,
        ano_atual, linha, grafico_estilo,
    )

elif secao == 'Comparar cenários':
    st.subheader('Compare cenários alternativos')
    st.caption('A comparação usa dados originais por cenário. Não mistura contas de cenários diferentes nem aplica probabilidades desconhecidas.')
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        c_a = st.selectbox('Cenário A', lista_cenarios, index=0, key='comparar_a',
                           format_func=lambda c: f'Cenário {c:05d}')
    with col_b:
        c_b = st.selectbox('Cenário B', lista_cenarios, index=1, key='comparar_b',
                           format_func=lambda c: f'Cenário {c:05d}')
    with col_c:
        incluir_terceiro = st.checkbox('Incluir cenário C', value=False)
        c_c = st.selectbox('Cenário C', lista_cenarios, index=2, key='comparar_c',
                           format_func=lambda c: f'Cenário {c:05d}', disabled=not incluir_terceiro)
    selecao_comp = [c_a, c_b] + ([c_c] if incluir_terceiro else [])
    if len(selecao_comp) != len(set(selecao_comp)):
        st.warning('Selecione cenários diferentes para uma comparação útil.')
    outro = df[df['cenario'].isin(selecao_comp) & df['ano'].between(*intervalo)].copy()
    outro_ano = outro[outro['ano'] == ano_atual].copy()
    campos_comp = ['receita', 'resultado_operacional', 'lucro_liquido',
                   'geracao_caixa', 'saldo_final_caixa', 'margem_operacional_pct']
    cols_exibir = ['Receita', 'Resultado operacional', 'Lucro líquido',
                   'Geração de caixa', 'Saldo final', 'Margem operacional']
    table = outro_ano[['cenario'] + campos_comp].rename(columns={'cenario':'Cenário', **dict(zip(campos_comp, cols_exibir))})
    table['Cenário'] = table['Cenário'].map(lambda x: f'{int(x):05d}')
    for col in cols_exibir[:-1]:
        table[col] = table[col].map(formatar_moeda)
    table['Margem operacional'] = table['Margem operacional'].map(formatar_percentual)
    st.dataframe(table, hide_index=True, use_container_width=True)
    metrica_comp = st.selectbox('Indicador a comparar na evolução', list(NOMES_METRICAS), index=4)
    campo_comp = NOMES_METRICAS[metrica_comp]
    valores_comp = outro[['ano','cenario',campo_comp]].copy()
    valores_comp['Cenário'] = valores_comp['cenario'].map(lambda x: f'Cenário {x:05d}')
    if '_pct' in campo_comp:
        ycol = 'Percentual (%)'
        valores_comp[ycol] = valores_comp[campo_comp]
    else:
        ycol = 'R$ bilhões'
        valores_comp[ycol] = valores_comp[campo_comp] / 1e9
    fig = px.line(valores_comp, x='ano', y=ycol, color='Cenário', markers=True,
                  title=f'{metrica_comp} por ano simulado', color_discrete_sequence=[COR_AZUL, COR_VERMELHO, COR_VERDE])
    st.plotly_chart(grafico_estilo(fig, 395), use_container_width=True)

    ano_todos = df[df['ano'] == ano_atual]
    distribuicao = ano_todos[[campo_comp]].copy()
    distribuicao['Indicador'] = distribuicao[campo_comp] if '_pct' in campo_comp else distribuicao[campo_comp] / 1e9
    fig_h = px.histogram(distribuicao, x='Indicador', nbins=38,
                          title=f'Distribuição dos 1.200 cenários no Ano {ano_atual}',
                          labels={'Indicador': 'Percentual (%)' if '_pct' in campo_comp else 'R$ bilhões'},
                          color_discrete_sequence=[COR_AZUL])
    st.plotly_chart(grafico_estilo(fig_h, 305), use_container_width=True)
    st.caption('O histograma é uma descrição dos cenários simulados; não representa uma distribuição probabilística validada.')

elif secao == 'Simulador':
    st.subheader('Simulador de sensibilidade')
    st.caption('Hipótese exploratória: variamos receita e custos da DRE; tributos, depreciação e demais contas permanecem constantes. Não recalculamos o fluxo de caixa.')
    st.info('**Como interpretar:** valores positivos aumentam a receita ou os custos; valores negativos reduzem esses valores. A simulação altera apenas o resultado operacional e a margem, mantendo as demais premissas constantes.')
    col_rec, col_custo = st.columns(2)
    with col_rec:
        v_receita = st.slider(
            'Alteração na receita (%)', -30, 30, 0, 1,
            help=('Percentual aplicado à receita do cenário e ano selecionados. '
                  '+10% aumenta a receita em 10%; -10% reduz a receita em 10%.')
        )
    with col_custo:
        v_custo = st.slider(
            'Alteração nos custos (%)', -30, 30, 0, 1,
            help=('Percentual aplicado ao tamanho (magnitude) dos custos da DRE. '
                  '+10% aumenta o valor dos custos em 10% (a saída fica maior); '
                  '-10% reduz os custos em 10%.')
        )
    nova_receita = linha['receita'] * (1 + v_receita / 100)
    novo_custo = linha['custos_dre'] * (1 + v_custo / 100)
    novo_resultado = (linha['resultado_operacional'] + (nova_receita - linha['receita'])
                      + (novo_custo - linha['custos_dre']))
    nova_margem = 100 * novo_resultado / nova_receita if nova_receita != 0 else np.nan
    col1,col2,col3 = st.columns(3)
    col1.metric('Receita simulada', formatar_moeda(nova_receita))
    col2.metric('Resultado operacional simulado', formatar_moeda(novo_resultado),
                delta=formatar_moeda(novo_resultado - linha['resultado_operacional']))
    col3.metric('Margem operacional simulada', formatar_percentual(nova_margem),
                delta=(f'{nova_margem - linha["margem_operacional_pct"]:+.2f} p.p.'.replace('.', ',')
                       if np.isfinite(nova_margem) else None))
    tabela_sim = pd.DataFrame({
        'Indicador': ['Receita','Custos da DRE (com sinal)','Resultado operacional','Margem operacional'],
        'Original': [formatar_moeda(linha['receita']), formatar_moeda(linha['custos_dre']),
                     formatar_moeda(linha['resultado_operacional']), formatar_percentual(linha['margem_operacional_pct'])],
        'Simulado': [formatar_moeda(nova_receita), formatar_moeda(novo_custo),
                     formatar_moeda(novo_resultado), formatar_percentual(nova_margem)],
    })
    st.dataframe(tabela_sim, hide_index=True, use_container_width=True)
    st.warning('**Importante:** esse exercício não é projeção oficial nem mensura efeitos de tributos, demanda, financiamento ou valor presente. Não use seus resultados como parecer de viabilidade.')

elif secao == 'Regressão':
    st.subheader('Regressão linear exploratória por ano simulado')
    st.caption('Ajuste linear descritivo entre ano simulado e um indicador. As observações são geradas por modelo/simulação; não representam amostra aleatória nem demonstram causalidade.')
    m_reg = st.selectbox('Indicador para o ajuste',
                         ['Receita da DRE','Lucro líquido','Geração líquida de caixa','Resultado operacional'],
                         index=0)
    campo = NOMES_METRICAS[m_reg]
    reg = regressao_temporal(por_ano, campo)
    if reg is None:
        st.info('Selecione no mínimo três anos simulados para estimar uma regressão.')
    else:
        m1,m2,m3,m4 = st.columns(4)
        m1.metric('Pontos utilizados', reg['n'])
        m2.metric('R²', f'{reg["r2"]:.3f}'.replace('.', ','))
        m3.metric('Inclinação por ano', formatar_moeda(reg['coeficiente_ano']))
        m4.metric('Erro absoluto médio', formatar_moeda(reg['mae']))
        df_reg = reg['tabela'].copy()
        df_reg['Observado (R$ bi)'] = df_reg['observado'] / 1e9
        df_reg['Ajuste (R$ bi)'] = df_reg['ajustado'] / 1e9
        df_plot = df_reg.melt(id_vars='ano', value_vars=['Observado (R$ bi)','Ajuste (R$ bi)'],
                              var_name='Série', value_name='R$ bilhões')
        fig = px.line(df_plot, x='ano', y='R$ bilhões', color='Série', markers=True,
                      title=f'Ajuste linear de {m_reg}', color_discrete_sequence=[COR_AZUL, COR_VERMELHO])
        st.plotly_chart(grafico_estilo(fig), use_container_width=True)
        fig_r = px.scatter(df_reg, x='ano', y='residuo', labels={'ano':'Ano simulado', 'residuo':'Resíduo (R$)'},
                           title='Resíduos do ajuste', color_discrete_sequence=[COR_VERMELHO])
        fig_r.add_hline(y=0, line_dash='dash', line_color=COR_CINZA)
        st.plotly_chart(grafico_estilo(fig_r, 290), use_container_width=True)
        st.caption(f'**Leitura:** a inclinação é de {formatar_moeda(reg["coeficiente_ano"])} por ano simulado. '
                   f'O R² é {reg["r2"]:.3f} e o RMSE é {formatar_moeda(reg["rmse"])}. '
                   'A inclinação descreve a reta ajustada; não demonstra tendência futura nem relação causal.')
        st.caption('O ajuste é uma etapa exploratória. Para cumprir integralmente os requisitos inferenciais, devem-se discutir pressupostos, independência e adequação do modelo no relatório técnico.')

elif secao == 'Qualidade e fontes':
    st.subheader('Rastreabilidade, qualidade e exportação')
    st.markdown('''**Fonte:** `Demonstrativo Fecap v3.csv`, fornecida no projeto CTI/FECAP.

**Unidade de observação:** par **ano simulado × cenário**. O setor da concessão e a moeda oficial não foram informados; a interface adota R$ para apresentação, conforme convenção do trabalho.

**Regras principais:**
- Receita, resultado operacional, EBITDA, lucro líquido, ativos, saldo inicial/final e fluxo são extraídos de contas de nome correspondente, sem recálculo da fonte.
- **Margens:** resultado correspondente ÷ receita da DRE × 100.
- **Média de cenários:** média aritmética de contas monetárias; margens calculadas como razão entre resultados médios e receita média, não como soma de cenários.
- **Ponte do caixa:** saldo inicial + (receita de caixa + tributos + custos + investimentos + resultado financeiro + IR/CSLL + distribuição a acionistas) = saldo final.
- **Resultado financeiro (FLU)** já resume entradas e despesas financeiras; essas duas contas não são adicionadas novamente à ponte.
- **EBITDA** é utilizado tal como registrado na DRE; não foi inferida uma reconciliação contábil que a fonte não documenta.
- **Meta de margem:** criada pelo usuário no painel, apenas para análise e não como meta oficial.
- **KPIs contábeis:** 25 definições da planilha `PI_Entrega01_Contabilidade_e_Financas.xlsx`, com valores por cenário e ano extraídos do cache de cálculo da própria planilha. Para médias entre cenários, razões são calculadas novamente a partir dos agregados ajustados.
- **Reclassificações contábeis:** passivo circulante ajustado, dívida onerosa e outros créditos seguem as decisões documentadas na planilha; índices originalmente apresentados na versão anterior do dashboard não sobrescrevem os KPIs da planilha.
- **EVA e MVA:** WACC de 10,5% a.a. conforme premissa da planilha, editável na aba Valor econômico; MVA contempla sempre os 12 anos.
- **Ano 12:** ausência de itens do balanço em parte da fonte; os indicadores afetados são apresentados como N/D.

**Limitações:** dados simulados; pesos/probabilidades não confirmados; setor desconhecido; os alertas não comprovam causalidade; há registros de ativo total negativo que exigem esclarecimento sobre as premissas; nenhuma validação substitui a revisão de um especialista de finanças.
''')
    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    col_q1.metric('Cenários na base', df['cenario'].nunique())
    col_q2.metric('Anos simulados', df['ano'].nunique())
    col_q3.metric('Pares ano/cenário', len(df))
    col_q4.metric('Ativos totais negativos', int((df['ativo_total'] < 0).sum()))
    fechamento_caixa = ((df['diferenca_geracao_caixa'].abs() < .01)
                       & (df['diferenca_saldo_caixa'].abs() < .01))
    if fechamento_caixa.all():
        st.success('Todos os 14.400 registros reconciliam no fluxo de caixa com tolerância de R$ 0,01.')
    else:
        st.error('Há divergências na reconciliação do fluxo de caixa; investigue antes da entrega.')
    st.caption('O balanço utiliza contas com sinais originais; foi identificada diferença residual aproximada de R$ 0,025 entre ativo e passivo totais, que não é zerada artificialmente.')
    st.divider()
    st.subheader('Materiais para auditoria e apresentação')
    arq_recorte = sub.to_csv(index=False).encode('utf-8-sig')
    relatorio = resumo_executivo(linha, ano_atual, titulo_recorte, meta)
    d1,d2 = st.columns(2)
    with d1:
        st.download_button('⬇ Exportar dados selecionados (CSV)', data=arq_recorte,
                           file_name='cti_dados_selecionados.csv', mime='text/csv', use_container_width=True)
    with d2:
        st.download_button('⬇ Resumo executivo (Markdown)', data=relatorio.encode('utf-8'),
                           file_name='cti_resumo_executivo.md', mime='text/markdown', use_container_width=True)
    with st.expander('Visualizar resumo executivo'):
        st.markdown(relatorio)
    with st.expander('Glossário rápido para a apresentação'):
        st.markdown('''- **Receita:** valor reconhecido como receita na DRE, não necessariamente recebido integralmente em caixa.
- **Resultado operacional:** resultado das atividades operacionais segundo a DRE fornecida.
- **Lucro líquido:** resultado contábil após os itens que compõem a DRE.
- **EBITDA:** resultado antes de juros, tributos sobre lucro, depreciação e amortização, usado aqui no valor informado pela CTI.
- **Margem operacional:** quanto o resultado operacional representa da receita, em percentual.
- **Geração líquida de caixa:** efeito líquido de entradas e saídas no período, conforme o FLU.
- **Saldo final de caixa:** saldo inicial ajustado pela geração líquida de caixa.
- **Análise de sensibilidade:** exploração de cenários hipotéticos, alterando premissas explicitadas.
- **Regressão linear:** reta matemática ajustada aos dados; exige cautela para interpretação inferencial.''')
    st.code('python scripts/preparar_dados.py\npython scripts/validar_dados.py\npython -m streamlit run app.py', language='bash')

st.divider()
st.caption('CTI • Projeto Interdisciplinar FECAP • Fonte original preservada • Valores em R$ como convenção de apresentação • Cenários simulados')
