"""Gera a base analítica do projeto a partir do CSV bruto sem modificá-lo.

A granularidade é (ano simulado, cenário), com números e sinais originais.
"""
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
FONTE = RAIZ / 'dados' / 'Demonstrativo Fecap v3.csv'
SAIDA = RAIZ / 'dados' / 'indicadores_cti.csv'

# A nomenclatura abaixo é idêntica à do demonstrativo recebido da CTI.
CONTAS = {
    'DRE - Receita': 'receita',
    'DRE - Tributos': 'tributos_dre',
    'DRE - Custos': 'custos_dre',
    'DRE - Depreciação e Amortização': 'depreciacao_amortizacao_dre',
    'DRE - Resultado Operacional': 'resultado_operacional',
    'DRE - EBITDA': 'ebitda',
    'DRE - Resultado Líquido': 'lucro_liquido',
    'BAL - Total do Ativo': 'ativo_total',
    'BAL - Ativo Circulante': 'ativo_circulante',
    'BAL - Disponível': 'disponivel',
    'BAL - Contas a Receber - Clientes': 'contas_receber_clientes',
    'BAL - Estoques Diversos': 'estoques',
    'BAL - Total do Passivo': 'passivo_total',
    'BAL - Passivo Circulante': 'passivo_circulante',
    'BAL  - Patrimônio Líquido': 'patrimonio_liquido',
    'FLU - Saldo Inicial': 'saldo_inicial_caixa',
    'FLU - Receita': 'receita_caixa',
    'FLU - Tributos': 'tributos_caixa',
    'FLU - Custos': 'custos_caixa',
    'FLU - Investimentos': 'investimentos_caixa',
    'FLU - Entradas': 'entradas_financeiras_caixa',
    'FLU - Despesas Financeiras': 'despesas_financeiras_caixa',
    'FLU - Resultado Financeiro': 'resultado_financeiro_caixa',
    'FLU - Imposto de Renda e Contribuição Social': 'ir_csll_caixa',
    'FLU - Distribuição para Acionista': 'distribuicao_acionista_caixa',
    'FLU - Geração de Caixa': 'geracao_caixa',
    'FLU - Saldo Final': 'saldo_final_caixa',
}

COMPONENTES_CAIXA = [
    'receita_caixa', 'tributos_caixa', 'custos_caixa',
    'investimentos_caixa', 'resultado_financeiro_caixa',
    'ir_csll_caixa', 'distribuicao_acionista_caixa',
]


def numero_br(coluna):
    """Interpreta separadores pt-BR, incluindo -0 e decimais pequenos."""
    return pd.to_numeric(
        coluna.str.replace('.', '', regex=False).str.replace(',', '.', regex=False),
        errors='raise',
    )


def executar():
    fonte = pd.read_csv(
        FONTE, sep=';', encoding='latin-1', header=None,
        names=['ano', 'cenario', 'conta', 'valor'], dtype=str,
        keep_default_na=False,
    )
    filtrado = fonte.loc[fonte['conta'].isin(CONTAS)].copy()
    filtrado['ano'] = filtrado['ano'].str.extract(r'(\d+)')[0].astype(int)
    filtrado['cenario'] = filtrado['cenario'].str.extract(r'(\d+)')[0].astype(int)
    filtrado['valor'] = numero_br(filtrado['valor'])

    if filtrado.duplicated(['ano', 'cenario', 'conta']).any():
        raise ValueError('Contas duplicadas para o mesmo ano e cenário.')

    tabela = (filtrado.pivot(index=['ano', 'cenario'], columns='conta', values='valor')
              .rename(columns=CONTAS).reset_index().sort_values(['cenario', 'ano']))
    # Algumas contas analíticas do balanço não são informadas em todos os
    # períodos da fonte; nesse caso, a ausência representa saldo zero.
    campos_opcionais = ['estoques', 'patrimonio_liquido']
    for campo in campos_opcionais:
        if campo in tabela:
            tabela[campo] = tabela[campo].fillna(0)
    if len(tabela) != 14_400 or tabela[list(CONTAS.values())].isna().any().any():
        raise ValueError('Faltam combinações ou campos obrigatórios na fonte.')

    # Indicadores derivados apenas quando a Receita é diferente de zero.
    receita_valida = tabela['receita'].where(tabela['receita'] != 0)
    tabela['margem_operacional_pct'] = tabela['resultado_operacional'] / receita_valida * 100
    tabela['margem_liquida_pct'] = tabela['lucro_liquido'] / receita_valida * 100
    tabela['margem_ebitda_pct'] = tabela['ebitda'] / receita_valida * 100

    # Mantém visíveis diferenças de reconciliação e não altera as contas da CTI.
    tabela['diferenca_geracao_caixa'] = tabela[COMPONENTES_CAIXA].sum(axis=1) - tabela['geracao_caixa']
    tabela['diferenca_saldo_caixa'] = (tabela['saldo_inicial_caixa'] + tabela['geracao_caixa']
                                     - tabela['saldo_final_caixa'])
    tabela['diferenca_balanco'] = tabela['ativo_total'] + tabela['passivo_total']
    tabela.to_csv(SAIDA, index=False, encoding='utf-8-sig', float_format='%.17g')
    print(f'Gerados {len(tabela):,} registros / {len(tabela.columns)} colunas: {SAIDA}')
    print('Maior diferença de componentes do caixa: R$', tabela['diferenca_geracao_caixa'].abs().max())
    print('Maior diferença de saldo: R$', tabela['diferenca_saldo_caixa'].abs().max())
    return tabela


if __name__ == '__main__':
    executar()
