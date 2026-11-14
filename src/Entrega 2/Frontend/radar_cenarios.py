"""Interface Radar de Cenários do DashBird, com seleção de pontos no Plotly."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.radar import CATEGORIAS, CORES_CATEGORIAS, preparar_radar, resumo_radar, diagnostico_cenario


def _grafico_radar(dados: pd.DataFrame, limite: float):
    fig = go.Figure()
    for categoria in CATEGORIAS:
        parte = dados[dados["grupo"] == categoria]
        if parte.empty:
            continue
        fig.add_trace(go.Scatter(
            x=parte["margem_operacional_pct"],
            y=parte["geracao_caixa_bi"],
            customdata=parte[["cenario"]].astype(int).to_numpy(),
            mode="markers",
            name=categoria,
            marker=dict(color=CORES_CATEGORIAS[categoria], size=8, opacity=.75,
                        line=dict(color="#0A1523", width=.5)),
            hovertemplate=(
                "<b>Cenário %{customdata[0]:05d}</b>"
                "<br>Margem operacional: %{x:.2f}%"
                "<br>Geração de caixa: R$ %{y:.3f} bi"
                "<extra></extra>"
            ),
        ))
    fig.add_hline(y=0, line_color="#8EA5BA", line_width=1.1, line_dash="dash")
    fig.add_vline(x=limite, line_color="#8EA5BA", line_width=1.1, line_dash="dot")
    fig.update_layout(
        height=510,
        margin=dict(l=20, r=15, t=16, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#0C1B2D",
        font=dict(family="Inter, Segoe UI, sans-serif", color="#C7D4E2", size=11),
        legend=dict(orientation="h", yanchor="top", y=-.18, x=0, xanchor="left",
                    font=dict(size=10)),
        hovermode="closest",
        dragmode="select",
        clickmode="event+select",
        xaxis=dict(title="Margem operacional (%)", gridcolor="#233A51", zeroline=False,
                   tickformat=".1f"),
        yaxis=dict(title="Geração líquida de caixa (R$ bilhões)",
                   gridcolor="#233A51", zeroline=False, tickformat=".2f"),
    )
    return fig


def _cenario_clicado(evento):
    """Extrai identificador do customdata, sem depender do índice dos traços."""
    try:
        pontos = evento["selection"]["points"]
        if not pontos:
            return None
        identificador = pontos[-1].get("customdata", [None])[0]
        return int(identificador) if identificador is not None else None
    except (TypeError, IndexError, KeyError, ValueError, AttributeError):
        return None


def mostrar_radar(base: pd.DataFrame, ano: int, meta: float, formatar_moeda, formatar_percentual):
    """Mostra todos os cenários do ano, independentemente do filtro lateral."""
    st.markdown(
        '<div class="page-eyebrow">EXPLORAR • COMPARAR • COMPREENDER</div>',
        unsafe_allow_html=True,
    )
    st.subheader("Radar Inteligente de Cenários")
    st.caption(
        "Cada ponto é um cenário simulado no ano escolhido. "
        "Clique em um ponto para investigar seus números e entender o diagnóstico automático."
    )

    modo = st.radio(
        "Referência para a margem operacional",
        ["Mediana dos cenários no ano", "Meta ajustada nas preferências"],
        horizontal=True,
        help="A mediana divide os valores centrais dos cenários no ano. A meta é uma referência "
             "de análise informada pelo usuário, não uma meta oficial da CTI.",
        key="radar_modo_referencia",
    )
    ref_manual = float(meta) if modo == "Meta ajustada nas preferências" else None
    dados, limite, invalidos = preparar_radar(base, ano, ref_manual)
    if dados.empty:
        st.warning("Não há cenários com margem e geração de caixa válidas no período selecionado.")
        return

    dados_resumo = resumo_radar(dados)
    n_total = dados_resumo["total"]
    n_caixa_neg = dados_resumo["caixa_negativo"]
    dupla_atencao = dados_resumo["por_grupo"][CATEGORIAS[3]]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cenários no Radar", f"{n_total:,}".replace(",", "."))
    c2.metric("Caixa negativo", f"{n_caixa_neg:,}".replace(",", "."))
    c3.metric("Margem de referência", formatar_percentual(limite))
    c4.metric("Dois sinais de atenção", f"{dupla_atencao:,}".replace(",", "."))
    st.caption(
        "**Critérios:** margem abaixo da referência e/ou geração líquida de caixa negativa. "
        "As cores representam combinações desses dois sinais, não graus de risco."
    )

    esquerda, direita = st.columns([1.75, .95], gap="large")
    with esquerda:
        figura = _grafico_radar(dados, limite)
        # A seleção pode retornar pontos de qualquer traço. O ID do cenário está no customdata.
        key_plot = f"radar_pontos_{ano}_{'meta' if ref_manual is not None else 'mediana'}_{limite:.4f}"
        evento = st.plotly_chart(
            figura, use_container_width=True, theme=None,
            key=key_plot, on_select="rerun", selection_mode="points",
            config={"displaylogo": False, "scrollZoom": False},
        )
        st.caption(
            "Linha vertical: margem de referência. Linha horizontal: geração líquida "
            "de caixa igual a zero. Os 1.200 cenários são mostrados independentemente "
            "da seleção individual da barra lateral."
        )
        if invalidos:
            st.warning(f"{invalidos} cenário(s) ficaram de fora por valores indisponíveis nos eixos.")

    with direita:
        st.markdown("#### Diagnóstico do cenário")
        ids = dados["cenario"].astype(int).tolist()
        chave_selecionado = f"radar_escolha_{ano}"
        chave_ultimo = f"radar_ultimo_ponto_{ano}"
        if st.session_state.get(chave_selecionado) not in ids:
            st.session_state[chave_selecionado] = ids[0]

        clicado = _cenario_clicado(evento)
        if clicado is not None and clicado in ids and clicado != st.session_state.get(chave_ultimo):
            st.session_state[chave_selecionado] = clicado
            st.session_state[chave_ultimo] = clicado

        selecionado = st.selectbox(
            "Cenário para inspecionar",
            ids,
            format_func=lambda c: f"Cenário {c:05d}",
            key=chave_selecionado,
            help="Selecione pela lista ou clique em um ponto do gráfico.",
        )
        linha = dados.loc[dados["cenario"] == selecionado].iloc[0]
        st.markdown(f"**{linha['grupo']}**")
        st.info(diagnostico_cenario(linha, limite))
        d1, d2 = st.columns(2)
        d1.metric("Margem operacional", formatar_percentual(linha["margem_operacional_pct"]))
        d2.metric("Geração de caixa", formatar_moeda(linha["geracao_caixa"]))
        d3, d4 = st.columns(2)
        d3.metric("Receita", formatar_moeda(linha["receita"]))
        d4.metric("Lucro líquido", formatar_moeda(linha["lucro_liquido"]))
        st.caption(
            "Diagnóstico construído com regras transparentes: não utiliza IA generativa "
            "nem prevê a probabilidade dos resultados."
        )

    st.markdown("#### Compare o cenário selecionado com o conjunto")
    comparacoes = (
        ("Margem operacional", "margem_operacional_pct", True),
        ("Geração de caixa", "geracao_caixa", False),
        ("Receita", "receita", False),
        ("Resultado operacional", "resultado_operacional", False),
        ("Lucro líquido", "lucro_liquido", False),
    )
    tabela = []
    for nome, campo, percentual in comparacoes:
        mediana = pd.to_numeric(dados[campo], errors="coerce").replace([np.inf, -np.inf], np.nan).median()
        formatar = formatar_percentual if percentual else formatar_moeda
        tabela.append({
            "Indicador": nome,
            f"Cenário {selecionado:05d}": formatar(linha[campo]),
            f"Mediana dos {n_total} cenários": formatar(mediana),
        })
    st.dataframe(pd.DataFrame(tabela), hide_index=True, use_container_width=True)
    st.caption(
        "Esta visualização é descritiva. Os cenários não possuem probabilidades "
        "validadas, e a posição no gráfico não determina risco, causalidade ou viabilidade. "
        "O Ano 12 contém particularidades na estrutura da base e deve ser interpretado separadamente."
    )
