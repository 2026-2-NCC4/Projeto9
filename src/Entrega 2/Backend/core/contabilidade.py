"""Integração fiel à planilha da Entrega 1 de Contabilidade e Finanças.

Os valores-base, ajustes de balanço e KPIs originais provêm da aba
05_KPIs_por_Cenario_Ano da planilha fornecida pelo usuário.
Para médias de cenários, os *quocientes* são recalculados sobre as médias
simples de seus componentes, para evitar médias de razões incompatíveis.
A simulação de WACC afeta somente EVA e MVA; demais contas são preservadas.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]

INDICADORES = {
    'LC': ('Liquidez Corrente', 'lc', 'x', 'Liquidez'),
    'LS': ('Liquidez Seca', 'ls', 'x', 'Liquidez'),
    'LI': ('Liquidez Imediata', 'li', 'x', 'Liquidez'),
    'LG': ('Liquidez Geral', 'lg', 'x', 'Liquidez'),
    'CCL': ('Capital Circulante Líquido', 'ccl', 'reais', 'Liquidez'),
    'ICC': ('Índice de Cobertura de Caixa', 'icc', 'x', 'Liquidez'),
    'EG': ('Endividamento Geral', 'eg', 'pct', 'Endividamento'),
    'PCT': ('Participação de Capital de Terceiros', 'pct', 'x', 'Endividamento'),
    'CE': ('Composição do Endividamento', 'ce', 'pct', 'Endividamento'),
    'IPL': ('Imobilização do Patrimônio Líquido', 'ipl', 'x', 'Endividamento'),
    'IRNC': ('Imobilização dos Recursos Não Correntes', 'irnc', 'x', 'Endividamento'),
    'GEF': ('Grau de Endividamento Financeiro', 'gef', 'x', 'Endividamento'),
    'DLE': ('Dívida Líquida / EBITDA', 'dle', 'x', 'Endividamento'),
    'ICJ': ('Índice de Cobertura de Juros', 'icj', 'x', 'Endividamento'),
    'MAF': ('Multiplicador de Alavancagem Financeira', 'maf', 'x', 'Endividamento'),
    'EBITDA': ('EBITDA informado', 'ebitda_informado_planilha', 'reais', 'Resultado'),
    'EBITDA_rec': ('EBITDA recalculado', 'ebitda_recalculado', 'reais', 'Resultado'),
    'MargEBITDA': ('Margem EBITDA', 'marg_ebitda', 'pct', 'Resultado'),
    'MargLiquida': ('Margem Líquida', 'marg_liquida', 'pct', 'Resultado'),
    'ROE': ('Retorno sobre o Patrimônio Líquido', 'roe', 'pct', 'Resultado'),
    'ROA': ('Retorno sobre o Ativo', 'roa', 'pct', 'Resultado'),
    'NOPAT': ('Lucro Operacional Líquido de Impostos', 'nopat', 'reais', 'Valor'),
    'CI': ('Capital Investido', 'capital_investido', 'reais', 'Valor'),
    'EVA': ('Valor Econômico Agregado (EVA)', 'eva', 'reais', 'Valor'),
    'MVA': ('Valor Econômico do Horizonte (MVA)', 'mva', 'reais', 'Valor'),
}

# Reprodução das fórmulas da aba 01_Dicionario_KPIs, usando os agregados
# reclassificados da aba 05_KPIs_por_Cenario_Ano.
RAZOES = {
    'lc': ('ativo_circulante_aj', 'passivo_circulante_aj'),
    'li': ('disponivel_planilha', 'passivo_circulante_aj'),
    'icc': ('geracao_caixa_planilha', 'passivo_circulante_aj'),
    'eg': ('capital_terceiros', 'ativo_total_aj'),
    'pct': ('capital_terceiros', 'patrimonio_liquido_planilha'),
    'ce': ('passivo_circulante_aj', 'capital_terceiros'),
    'ipl': ('permanente', 'patrimonio_liquido_planilha'),
    'gef': ('divida_onerosa', 'patrimonio_liquido_planilha'),
    'dle': ('divida_liquida', 'ebitda_informado_planilha'),
    'icj': ('ebit', 'despesas_financeiras'),
    'maf': ('ativo_total_aj', 'patrimonio_liquido_planilha'),
    'marg_ebitda': ('ebitda_informado_planilha', 'receita_liquida_planilha'),
    'marg_liquida': ('lucro_liquido_planilha', 'receita_liquida_planilha'),
    'roe': ('lucro_liquido_planilha', 'patrimonio_liquido_planilha'),
    'roa': ('lucro_liquido_planilha', 'ativo_total_aj'),
}


def carregar_planilha_convertida():
    path = RAIZ / 'dados' / 'kpis_contabilidade.csv'
    base = pd.read_csv(path, encoding='utf-8')
    if base.duplicated(['cenario', 'ano']).any():
        raise ValueError('Há duplicações no recorte ano/cenário da planilha.')
    if len(base) != 14400:
        raise ValueError(f'Esperados 14.400 registros da planilha; encontrados {len(base)}.')
    return base


def carregar_dicionario():
    path = RAIZ / 'relatorios' / 'dicionario_kpis_planilha.json'
    with path.open(encoding='utf-8') as f:
        data = json.load(f)
    if len(data) != len(INDICADORES):
        raise ValueError('Dicionário incompleto: esperados 25 KPIs.')
    return data


def carregar_ranking():
    return pd.read_csv(RAIZ / 'dados' / 'ranking_contabilidade.csv', encoding='utf-8')


def calcular_eva(base, wacc=0.105):
    """EVA = NOPAT do ano - WACC × capital investido na abertura."""
    resultado = base.copy()
    resultado['eva'] = resultado['nopat'] - wacc * resultado['capital_investido_abertura']
    return resultado


def calcular_mva(base_completa, cenarios, wacc=0.105):
    """MVA por cenário = soma EVA(t)/(1+WACC)^t, sempre nos 12 anos.

    Depois tira média *de valores MVA por cenário*, sem somar cenários.
    """
    if wacc <= -1:
        return np.nan
    dados = calcular_eva(base_completa[base_completa['cenario'].isin(cenarios)], wacc)
    if dados.empty:
        return np.nan
    valores = dados.assign(presente=dados['eva'] / (1.0 + wacc) ** dados['ano'])
    por_cenario = valores.groupby('cenario').agg(mva=('presente', 'sum'), anos=('ano', 'nunique'))
    validos = por_cenario[por_cenario['anos'] == 12]
    return float(validos.mva.mean()) if len(validos) else np.nan


def agregar_por_ano(recorte, wacc=0.105):
    """Mantém valores oficiais por cenário e recompõe quocientes quando há média."""
    if recorte.empty:
        return recorte.copy()
    base = calcular_eva(recorte, wacc)
    if base['cenario'].nunique() == 1:
        return base.sort_values('ano').reset_index(drop=True)
    numeros = base.select_dtypes(include=[np.number]).columns.difference(['ano', 'ano_num', 'cenario'])
    agregado = base.groupby('ano', as_index=False)[list(numeros)].mean()

    def fracao(numerador, denominador, valor_absoluto=False):
        den = agregado[denominador].abs() if valor_absoluto else agregado[denominador]
        return agregado[numerador] / den.where(den != 0)

    for destino, (num, den) in RAZOES.items():
        agregado[destino] = fracao(num, den, valor_absoluto=(destino == 'icj'))
    agregado['ls'] = fracao('ativo_circulante_aj', 'passivo_circulante_aj') - fracao('estoques_planilha', 'passivo_circulante_aj')
    agregado['lg'] = ((agregado['ativo_circulante_aj'] + agregado['realizavel_lp']) /
                      (agregado['passivo_circulante_aj'] + agregado['exigivel_lp_aj']).replace(0, np.nan))
    agregado['irnc'] = (agregado['permanente'] /
                        (agregado['patrimonio_liquido_planilha'] + agregado['exigivel_lp_aj']).replace(0, np.nan))
    agregado['ccl'] = agregado['ativo_circulante_aj'] - agregado['passivo_circulante_aj']
    agregado['eva'] = agregado['nopat'] - wacc * agregado['capital_investido_abertura']
    # Índices com PL não positivo não admitem interpretação econômica usual.
    for campo in ('pct', 'ipl', 'gef', 'maf', 'roe'):
        agregado.loc[agregado['patrimonio_liquido_planilha'] <= 0, campo] = np.nan
    return agregado.sort_values('ano').reset_index(drop=True)


def ano_mais_recente_com_liquidez(dados_por_ano):
    """Recomenda o último ano com todos os seis indicadores de liquidez disponíveis.

    A base da Entrega 1 não traz o passivo circulante ajustado no Ano 12.
    Sem o denominador, não é correto estimar os índices nem exibir zero.
    """
    if dados_por_ano.empty:
        return None
    campos = ('lc', 'ls', 'li', 'lg', 'ccl', 'icc')
    validos = dados_por_ano.loc[
        dados_por_ano[list(campos)].notna().all(axis=1), 'ano'
    ]
    if not validos.empty:
        return int(validos.max())
    return int(dados_por_ano['ano'].max())


def formatar_kpi(valor, unidade):
    if valor is None or pd.isna(valor) or not np.isfinite(float(valor)):
        return 'N/D'
    if unidade == 'reais':
        from core.analise import formatar_moeda
        return formatar_moeda(valor)
    if unidade == 'pct':
        return f'{float(valor)*100:,.2f}%'.replace(',', 'T').replace('.', ',').replace('T', '.')
    return f'{float(valor):,.2f}x'.replace(',', 'T').replace('.', ',').replace('T', '.')


def indicador_tabela(linha, ids, mva=np.nan):
    data = []
    for ident in ids:
        nome, chave, unidade, categoria = INDICADORES[ident]
        valor = mva if ident == 'MVA' else linha.get(chave, np.nan)
        if ident in ('PCT', 'IPL', 'GEF', 'MAF', 'ROE') and linha.get('patrimonio_liquido_planilha', np.nan) <= 0:
            valor = np.nan
        data.append({'Categoria': categoria, 'Indicador': nome,
                     'Valor': formatar_kpi(valor, unidade), 'ID': ident})
    return pd.DataFrame(data)
