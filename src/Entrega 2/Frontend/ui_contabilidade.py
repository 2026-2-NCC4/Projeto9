"""Visão integrada da Entrega 1 de Contabilidade e dos indicadores CTI.

A navegação principal fica enxuta; os 25 KPIs aparecem agrupados
internamente em abas, sem expor os códigos acadêmicos 8_..., 9_... etc.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from core.analise import (
    dva_modelo_aula, fluxo_caixa_componentes, formatar_moeda,
    formatar_percentual, indices_dfc,
)
from core.contabilidade import (
    INDICADORES, agregar_por_ano, calcular_mva,
    carregar_dicionario, formatar_kpi, indicador_tabela,
)

CORES = ['#69A9FF', '#39C7AE', '#F5B66D', '#F0717D']
LIQUIDEZ = ['LC', 'LS', 'LI', 'LG', 'CCL', 'ICC']
ENDIVIDAMENTO = ['EG', 'PCT', 'CE', 'IPL', 'IRNC', 'GEF', 'DLE', 'ICJ', 'MAF']
RESULTADO = ['EBITDA', 'EBITDA_rec', 'MargEBITDA', 'MargLiquida', 'ROE', 'ROA']
VALOR = ['NOPAT', 'CI', 'EVA', 'MVA']


def _valor(linha, ident, mva):
    if ident == 'MVA':
        return mva
    campo = INDICADORES[ident][1]
    valor = linha.get(campo, np.nan)
    if ident in {'PCT', 'IPL', 'GEF', 'MAF', 'ROE'} and linha.get('patrimonio_liquido_planilha', np.nan) <= 0:
        return np.nan
    return valor


def _cartoes(linha, ids, mva=np.nan, n=3):
    for comeco in range(0, len(ids), n):
        cols = st.columns(n, gap='medium')
        for col, codigo in zip(cols, ids[comeco:comeco + n]):
            nome, _, unidade, _ = INDICADORES[codigo]
            col.metric(nome, formatar_kpi(_valor(linha, codigo, mva), unidade))


def _plot_indicadores(dados, ids, titulo, estilizacao, tipo='line'):
    if len(dados) == 0:
        st.info('Não há dados disponíveis para esse intervalo.')
        return
    partes = []
    for ident in ids:
        nome, campo, unidade, _ = INDICADORES[ident]
        if campo not in dados or unidade == 'reais' and ident == 'MVA':
            continue
        aux = dados[['ano', campo]].copy()
        aux = aux.rename(columns={campo: 'Valor'})
        aux['Indicador'] = nome
        if unidade == 'reais':
            aux['Valor'] /= 1e9
        elif unidade == 'pct':
            aux['Valor'] *= 100
        partes.append(aux)
    if not partes:
        st.info('Este indicador não está disponível no intervalo escolhido.')
        return
    base = pd.concat(partes, ignore_index=True).dropna(subset=['Valor'])
    if base.empty:
        st.info('Este indicador não está disponível no intervalo escolhido.')
        return
    unidade = INDICADORES[ids[0]][2]
    y_label = {'reais': 'R$ bilhões', 'pct': '%', 'x': 'vezes (x)'}[unidade]
    if tipo == 'bar':
        fig = px.bar(base, x='ano', y='Valor', color='Indicador', barmode='group',
                     title=titulo, color_discrete_sequence=CORES)
    else:
        fig = px.line(base, x='ano', y='Valor', color='Indicador', markers=True,
                      title=titulo, color_discrete_sequence=CORES)
    fig.update_layout(yaxis_title=y_label, xaxis_title='Ano simulado')
    st.plotly_chart(estilizacao(fig, 325), use_container_width=True)


def mostrar_painel(base_completa, cenarios, intervalo, ano_atual, linha_cti, estilo):
    if not cenarios:
        st.warning('Selecione ao menos um cenário.')
        return
    wacc_percentual = float(st.session_state.get('cti_wacc', 10.5))
    wacc = wacc_percentual / 100
    recorte = base_completa[
        base_completa['cenario'].isin(cenarios) & base_completa['ano'].between(*intervalo)
    ]
    dados = agregar_por_ano(recorte, wacc)
    if dados.empty or ano_atual not in dados['ano'].values:
        st.warning('Não há indicadores contábeis para os filtros selecionados.')
        return
    linha = dados.loc[dados['ano'] == ano_atual].iloc[0]
    mva = calcular_mva(base_completa, cenarios, wacc)
    st.markdown('<div class="page-eyebrow">ANÁLISE INTEGRADA • CONTABILIDADE & FINANÇAS</div>', unsafe_allow_html=True)
    st.subheader('Indicadores contábeis e financeiros')
    st.caption('25 KPIs da planilha da Entrega 1, integrados aos indicadores de desempenho, caixa e valor adicionado do painel. Todos respeitam o cenário e o ano escolhidos.')
    _cartoes(linha, ['LC', 'EG', 'MargEBITDA', 'EVA'], mva, n=4)
    st.caption('Percentuais exibidos em %, índices em vezes (x) e valores monetários em R$. As margens EBITDA e líquida da planilha utilizam RECEITA LÍQUIDA (Receita DRE + Tributos DRE); a margem operacional original do painel utiliza Receita da DRE antes dos tributos.')

    aba_resumo, aba_liquidez, aba_divida, aba_resultado, aba_valor, aba_caixa, aba_dic = st.tabs([
        'Panorama', 'Liquidez', 'Endividamento', 'Rentabilidade',
        'Valor econômico', 'Caixa e DVA', 'Dicionário dos 25 KPIs',
    ])

    with aba_resumo:
        st.markdown('#### Panorama de desempenho')
        st.caption('Evolução por ano simulado; nos múltiplos cenários, as contas são médias simples, e os quocientes são refeitos sobre essas médias.')
        a, b = st.columns(2)
        with a:
            _plot_indicadores(dados, ['LC', 'LS'], 'Liquidez corrente e seca', estilo)
        with b:
            _plot_indicadores(dados, ['EG', 'CE'], 'Dívida e composição do endividamento', estilo)
        c, d = st.columns(2)
        with c:
            _plot_indicadores(dados, ['MargEBITDA', 'MargLiquida'], 'Margens de resultado', estilo)
        with d:
            _plot_indicadores(dados, ['EVA'], 'Valor econômico criado por ano', estilo, tipo='bar')
        st.markdown('#### Painel completo no período selecionado')
        st.dataframe(indicador_tabela(linha, list(INDICADORES), mva=mva).drop(columns='ID'),
                     hide_index=True, use_container_width=True, height=535)
        st.caption('MVA representa o valor presente dos 12 anos simulados — não é um indicador apenas do ano selecionado.\n'
                   'Índices de balanço indisponíveis no Ano 12 aparecem como N/D, conforme a planilha original.')

    with aba_liquidez:
        st.markdown('#### Liquidez e capital circulante')
        if pd.isna(linha.get('lc', np.nan)):
            disponiveis = dados.loc[dados[['lc', 'ls', 'li', 'lg', 'ccl', 'icc']].notna().all(axis=1), 'ano']
            orientacao = (f'Selecione o **Ano {int(disponiveis.max())}** acima.' if len(disponiveis)
                          else 'Amplie o intervalo de anos na barra lateral para incluir o Ano 11.')
            st.info(
                f'Os índices de liquidez do **Ano {ano_atual}** estão indisponíveis na '
                'planilha porque faltam os saldos do Passivo Circulante Ajustado. '
                f'{orientacao} Não são preenchidos valores sem base contábil.'
            )
        _cartoes(linha, LIQUIDEZ)
        a, b = st.columns([1.3, .9])
        with a:
            _plot_indicadores(dados, ['LC', 'LS', 'LI', 'LG'], 'Cobertura das obrigações', estilo)
        with b:
            _plot_indicadores(dados, ['CCL'], 'Capital circulante líquido', estilo, tipo='bar')
        st.markdown('#### Contas usadas nas fórmulas')
        insumos = pd.DataFrame([
            ('Ativo circulante ajustado', linha.get('ativo_circulante_aj', np.nan)),
            ('Passivo circulante ajustado', linha.get('passivo_circulante_aj', np.nan)),
            ('Disponível', linha.get('disponivel_planilha', np.nan)),
            ('Estoques', linha.get('estoques_planilha', np.nan)),
            ('Realizável a longo prazo', linha.get('realizavel_lp', np.nan)),
            ('Exigível a longo prazo ajustado', linha.get('exigivel_lp_aj', np.nan)),
        ], columns=['Conta', 'Montante'])
        insumos['Valor'] = insumos['Montante'].map(formatar_moeda)
        st.dataframe(insumos[['Conta', 'Valor']], hide_index=True, use_container_width=True)
        st.info('As fórmulas utilizam o **passivo circulante ajustado e as reclassificações da planilha**, e não a magnitude simples do subtotal do balanço. Isso evita inconsistência entre as duas entregas.')

    with aba_divida:
        st.markdown('#### Endividamento e estrutura de capital')
        _cartoes(linha, ENDIVIDAMENTO)
        a, b = st.columns(2)
        with a:
            _plot_indicadores(dados, ['EG', 'CE'], 'Participação e prazo das dívidas', estilo)
        with b:
            _plot_indicadores(dados, ['DLE', 'ICJ'], 'Endividamento líquido e cobertura de juros', estilo)
        st.caption('O indicador Dívida Líquida / EBITDA pode ser negativo quando há caixa líquido superior à dívida. Patrimônio líquido não positivo limita a interpretação de indicadores baseados em PL.')

    with aba_resultado:
        st.markdown('#### Rentabilidade e resultados')
        _cartoes(linha, RESULTADO)
        a, b = st.columns(2)
        with a:
            _plot_indicadores(dados, ['EBITDA', 'EBITDA_rec'], 'EBITDA: informado × recalculado', estilo)
        with b:
            _plot_indicadores(dados, ['MargEBITDA', 'MargLiquida', 'ROE', 'ROA'], 'Rentabilidade ao longo dos anos', estilo)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric('Receita DRE (bruta)', formatar_moeda(linha_cti['receita']))
        c2.metric('Receita líquida (planilha)', formatar_moeda(linha.get('receita_liquida_planilha', np.nan)))
        c3.metric('Resultado operacional', formatar_moeda(linha_cti['resultado_operacional']))
        c4.metric('Lucro líquido', formatar_moeda(linha_cti['lucro_liquido']))
        st.warning('A planilha mostra diferença entre o EBITDA informado pela fonte e o EBITDA recalculado a partir das contas elementares. Ambos são exibidos separadamente; a divergência não foi ajustada artificialmente.')

    with aba_valor:
        st.markdown('#### Geração de valor econômico')
        st.caption('Os quatro indicadores seguem a metodologia descrita na planilha. Apenas o WACC abaixo é editável; a alíquota efetiva vem da base.')
        st.slider('WACC nominal anual (%)', min_value=7.5, max_value=13.5,
                  value=10.5, step=0.5, key='cti_wacc',
                  help='Premissa originalmente adotada na planilha: 10,5% a.a. Variações alteram EVA e MVA, sem alterar os demais indicadores.')
        _cartoes(linha, VALOR, mva=mva, n=4)
        a, b = st.columns(2)
        with a:
            _plot_indicadores(dados, ['NOPAT', 'EVA'], 'Lucro operacional líquido e EVA', estilo)
        with b:
            _plot_indicadores(dados, ['CI'], 'Capital investido', estilo, tipo='bar')
        st.markdown('**Fórmulas adotadas**')
        st.markdown('''- **NOPAT:** resultado operacional × (1 − alíquota efetiva).\n- **Capital investido:** patrimônio líquido + dívida onerosa.\n- **EVA:** NOPAT do período − WACC × capital investido de abertura.\n- **MVA:** soma dos 12 EVAs descontados por `(1 + WACC)^ano`.''')
        st.caption(f'O MVA considera o horizonte completo de 12 anos por cenário (WACC de {wacc_percentual:.1f}% a.a.), inclusive quando o filtro de período mostra menos anos. Nas médias, o MVA é a média dos MVAs por cenário; não soma cenários alternativos.')

    with aba_caixa:
        st.markdown('#### Fluxo de caixa e valor adicionado')
        st.caption('Indicadores de caixa e DVA que já existiam no dashboard, reunidos com os KPIs contábeis da planilha.')
        dfc = indices_dfc(linha_cti)
        cols = st.columns(4)
        for col, (nome, valor) in zip(cols, dfc.items()):
            col.metric(nome, formatar_percentual(valor))
        c1, c2, c3 = st.columns(3)
        c1.metric('Saldo inicial', formatar_moeda(linha_cti['saldo_inicial_caixa']))
        c2.metric('Geração líquida de caixa', formatar_moeda(linha_cti['geracao_caixa']))
        c3.metric('Saldo final', formatar_moeda(linha_cti['saldo_final_caixa']))
        fluxos = fluxo_caixa_componentes(linha_cti).copy()
        fluxos['R$ bilhões'] = fluxos['Valor'] / 1e9
        fig = px.bar(fluxos, x='R$ bilhões', y='Componente', orientation='h',
                     title='Entradas e saídas do fluxo de caixa',
                     color='Componente', color_discrete_sequence=CORES)
        st.plotly_chart(estilo(fig, 350), use_container_width=True)
        st.divider()
        st.markdown('#### Demonstração do Valor Adicionado (estimativa gerencial)')
        st.warning('Esta DVA é uma **estimativa gerencial**, não a DVA oficial: a fonte não discrimina pessoal e outras parcelas; capitais próprios é o resíduo da conciliação.')
        dva = dva_modelo_aula(linha_cti)
        cols = st.columns(4)
        for col, (nome, valor) in zip(cols, dva['indicadores'].items()):
            col.metric(nome, formatar_percentual(valor))
        dist = pd.DataFrame({'Grupo': list(dva['distribuicao']), 'Valor (R$)': list(dva['distribuicao'].values())})
        dist['Exibição'] = dist['Valor (R$)'].map(formatar_moeda)
        st.dataframe(dist[['Grupo', 'Exibição']], hide_index=True, use_container_width=True)
        st.caption('Não foram criadas categorias de distribuição sem suporte na fonte. Valores não informados são apresentados como N/D.')

    with aba_dic:
        st.markdown('#### Dicionário dos 25 indicadores')
        st.caption('Objetivos, fórmulas, unidades, fontes e validações extraídos da aba “01_Dicionario_KPIs” da planilha entregue na E1.')
        definicoes = carregar_dicionario()
        opcao = st.selectbox('Grupo de indicadores',
                             ['Todos', 'Liquidez', 'Endividamento', 'Resultado', 'Valor'])
        selecionados = [d for d in definicoes if opcao == 'Todos' or d['categoria'] == opcao]
        exibidos = pd.DataFrame([{k: d[k] for k in ['id', 'nome', 'categoria', 'formula', 'unidade', 'fonte']}
                                 for d in selecionados]).rename(columns={
                                     'id':'Código', 'nome':'Indicador', 'categoria':'Grupo',
                                     'formula':'Fórmula da planilha', 'unidade':'Unidade', 'fonte':'Fonte'})
        st.dataframe(exibidos, hide_index=True, use_container_width=True)
        if selecionados:
            nome_indice = st.selectbox('Ver interpretação e validação', [x['nome'] for x in selecionados])
            definicao = next(x for x in selecionados if x['nome'] == nome_indice)
            st.markdown('**Objetivo:** ' + definicao['objetivo'])
            st.markdown('**Regra de validação:** ' + definicao['validacao'])
            st.markdown('**Interpretação gerencial:** ' + definicao['interpretacao'])
        st.download_button('Exportar indicadores deste período (CSV)',
                           data=indicador_tabela(linha, list(INDICADORES), mva=mva).to_csv(index=False).encode('utf-8-sig'),
                           file_name='cti_indicadores_contabilidade.csv', mime='text/csv')
        st.caption('Premissa: WACC nominal 10,5% a.a. na planilha original; valores diferentes podem ser explorados na aba Valor econômico. Algumas classificações e o EBITDA informado exigem validação externa antes de uso profissional.')
