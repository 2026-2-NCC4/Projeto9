"""Cálculos e regras de sinalização para o painel da CTI.

Nenhuma análise automática estabelece relação de causa e efeito.
"""
import numpy as np
import pandas as pd

COMPONENTES = {
    'Recebimentos (FLU - Receita)': 'receita_caixa',
    'Tributos (FLU)': 'tributos_caixa',
    'Custos (FLU)': 'custos_caixa',
    'Investimentos (FLU)': 'investimentos_caixa',
    'Resultado financeiro (FLU)': 'resultado_financeiro_caixa',
    'IR e CSLL (FLU)': 'ir_csll_caixa',
    'Distribuição aos acionistas (FLU)': 'distribuicao_acionista_caixa',
}

NOMES_METRICAS = {
    'Receita da DRE': 'receita',
    'Resultado operacional': 'resultado_operacional',
    'EBITDA (informado)': 'ebitda',
    'Lucro líquido': 'lucro_liquido',
    'Geração líquida de caixa': 'geracao_caixa',
    'Saldo final de caixa': 'saldo_final_caixa',
    'Ativo total': 'ativo_total',
    'Margem operacional (%)': 'margem_operacional_pct',
    'Margem líquida (%)': 'margem_liquida_pct',
    'Margem EBITDA (%)': 'margem_ebitda_pct',
}

VALORES_MONETARIOS = [
    'receita', 'custos_dre', 'tributos_dre', 'depreciacao_amortizacao_dre',
    'resultado_operacional',
    'ebitda', 'lucro_liquido', 'saldo_inicial_caixa', 'saldo_final_caixa',
    'geracao_caixa', 'ativo_total', 'passivo_total', 'ativo_circulante',
    'disponivel', 'contas_receber_clientes', 'estoques', 'passivo_circulante',
    'patrimonio_liquido',
    *COMPONENTES.values(), 'entradas_financeiras_caixa', 'despesas_financeiras_caixa',
]


def recalcular_margens(tabela):
    """Para médias entre cenários, relação entre médias é diferente da média das margens."""
    t = tabela.copy()
    denom = t['receita'].where(t['receita'] != 0)
    t['margem_operacional_pct'] = t['resultado_operacional'] / denom * 100
    t['margem_liquida_pct'] = t['lucro_liquido'] / denom * 100
    t['margem_ebitda_pct'] = t['ebitda'] / denom * 100
    return t


def media_cenarios(tabela):
    """Cenários alternativos nunca são somados. Média simples, sem probabilidades."""
    campos = [c for c in VALORES_MONETARIOS if c in tabela.columns]
    medias = tabela.groupby('ano', as_index=False)[campos].mean()
    return recalcular_margens(medias)


def fluxo_caixa_componentes(linha):
    """Saídas são valores negativos; resultado financeiro inclui entradas/despesas financeiras."""
    return pd.DataFrame({
        'Componente': list(COMPONENTES),
        'Valor': [float(linha[c]) for c in COMPONENTES.values()],
    })


def indices_dfc(linha):
    """Índices descritivos do fluxo de caixa, sem interpretação causal."""
    receita = float(linha['receita'])
    base = abs(receita) if receita else np.nan
    return {
        'Geração de caixa / Receita': float(linha['geracao_caixa']) / base * 100,
        'Saldo final / Receita': float(linha['saldo_final_caixa']) / base * 100,
        'Investimentos / Receita': float(linha['investimentos_caixa']) / base * 100,
        'Distribuição / Geração de caixa': (
            abs(float(linha['distribuicao_acionista_caixa'])) /
            abs(float(linha['geracao_caixa'])) * 100
            if linha['geracao_caixa'] else np.nan
        ),
    }


def indices_capital_giro(linha):
    """Índices de liquidez calculados com os saldos do balanço original."""
    circulante = float(linha['ativo_circulante'])
    passivo = abs(float(linha['passivo_circulante']))
    return {
        'Capital de giro líquido': circulante - passivo,
        'Liquidez corrente': circulante / passivo if passivo else np.nan,
        'Liquidez seca': (circulante - float(linha['estoques'])) / passivo if passivo else np.nan,
        'Liquidez imediata': float(linha['disponivel']) / passivo if passivo else np.nan,
    }


def dva_modelo_aula(linha):
    """Monta uma DVA gerencial seguindo os itens 1 a 8 do modelo da aula.

    A fonte não separa pessoal, aluguéis e tributos recuperáveis. Nessas
    condições, capitais próprios é apresentado como residual de conciliação,
    e a resposta deve ser lida como estimativa gerencial, não como DVA oficial.
    """
    receitas = float(linha['receita'])
    insumos = abs(float(linha['custos_dre']))
    retencoes = abs(float(linha['depreciacao_amortizacao_dre']))
    transferencias = max(float(linha['entradas_financeiras_caixa']), 0.0)
    va_bruto = receitas - insumos
    va_liquido = va_bruto - retencoes
    va_total = va_liquido + transferencias
    pessoal = np.nan
    impostos = abs(float(linha['tributos_dre'])) + abs(float(linha['ir_csll_caixa']))
    terceiros = abs(float(linha['despesas_financeiras_caixa']))
    distribuicao_conhecida = impostos + terceiros
    capitais_proprios = va_total - distribuicao_conhecida
    distribuicao_total = distribuicao_conhecida + capitais_proprios
    return {
        'geracao': {
            'Receitas': receitas,
            '(-) Insumos adquiridos de terceiros': -insumos,
            'Valor adicionado bruto': va_bruto,
            '(-) Retenções': -retencoes,
            'Valor adicionado líquido produzido': va_liquido,
            '(+) Valor adicionado recebido em transferência': transferencias,
            'Valor adicionado total a distribuir': va_total,
        },
        'distribuicao': {
            'Pessoal (não informado)': pessoal,
            'Impostos, taxas e contribuições': impostos,
            'Remuneração de capitais de terceiros': terceiros,
            'Remuneração de capitais próprios (residual)': capitais_proprios,
            'Total distribuído': distribuicao_total,
        },
        'indicadores': {
            'Grau de geração de riqueza': va_total / abs(receitas) * 100 if receitas else np.nan,
            'Participação do governo': impostos / va_total * 100 if va_total else np.nan,
            'Participação de terceiros': terceiros / va_total * 100 if va_total else np.nan,
            'Retenção / VA total': capitais_proprios / va_total * 100 if va_total else np.nan,
        },
        'concilia': distribuicao_total - va_total,
    }


def conferir_caixa(linha):
    componentes = fluxo_caixa_componentes(linha)['Valor'].sum()
    inicial = float(linha['saldo_inicial_caixa'])
    geracao = float(linha['geracao_caixa'])
    final = float(linha['saldo_final_caixa'])
    return {
        'componentes': componentes,
        'diferenca_componentes': componentes - geracao,
        'diferenca_saldo': inicial + geracao - final,
        'ok': abs(componentes - geracao) < 0.01 and abs(inicial + geracao - final) < 0.01,
    }


def alertas(linha, meta_margem=None):
    """Retorna fatos descritivos e pontos a examinar, não interpretações causais."""
    lista = []
    if linha['lucro_liquido'] > 0 and linha['geracao_caixa'] < 0:
        lista.append(('atenção', 'Lucro positivo e caixa líquido negativo',
                      'O lucro contábil é positivo, mas o fluxo de caixa líquido do período é negativo. Examinar as saídas discriminadas na aba Caixa explicado.'))
    elif linha['lucro_liquido'] < 0:
        lista.append(('atenção', 'Resultado líquido negativo',
                      'A DRE informa prejuízo no período selecionado.'))
    if linha['saldo_final_caixa'] < 0:
        lista.append(('atenção', 'Saldo final de caixa negativo',
                      'A demonstração informa saldo final negativo. Verificar premissas e necessidades de financiamento.'))
    if linha['geracao_caixa'] < 0 and linha['distribuicao_acionista_caixa'] < 0:
        lista.append(('análise', 'Distribuição aos acionistas no período',
                      'Há distribuição aos acionistas registrada junto com uma geração líquida de caixa negativa. Ela integra as saídas, sem que isso por si só explique toda a variação.'))
    if linha['ativo_total'] < 0:
        lista.append(('qualidade', 'Ativo total negativo no dado original',
                      'O balanço apresenta ativo total negativo. É necessário esclarecer a natureza da simulação e a convenção da fonte.'))
    if meta_margem is not None and np.isfinite(linha['margem_operacional_pct']):
        if linha['margem_operacional_pct'] < meta_margem:
            lista.append(('meta', 'Margem abaixo da meta definida pelo usuário',
                          'Comparação com uma meta de análise configurada no painel; não é uma meta oficial da CTI.'))
    if not lista:
        lista.append(('informação', 'Sem alertas nas regras automáticas',
                      'As verificações automáticas não encontraram os casos previstos. Isso não garante a viabilidade da concessão.'))
    return lista


def regressao_temporal(serie, campo):
    """Ajuste descritivo linear nos anos simulados, sem extrapolação ou causalidade."""
    s = serie[['ano', campo]].dropna().sort_values('ano')
    if len(s) < 3 or s['ano'].nunique() < 3:
        return None
    x = s.ano.to_numpy(dtype=float)
    y = s[campo].to_numpy(dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    yhat = slope * x + intercept
    residuo = y - yhat
    ss_res = float(np.sum(residuo ** 2))
    ss_total = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_total if ss_total > 0 else np.nan
    return {
        'tabela': pd.DataFrame({'ano': x.astype(int), 'observado': y, 'ajustado': yhat, 'residuo': residuo}),
        'coeficiente_ano': float(slope), 'intercepto': float(intercept),
        'r2': r2, 'mae': float(np.mean(np.abs(residuo))),
        'rmse': float(np.sqrt(np.mean(residuo ** 2))), 'n': len(s),
    }


def formatar_moeda(valor, decimais=2):
    if pd.isna(valor):
        return 'N/D'
    a = abs(float(valor))
    if a >= 1e9:
        base, unid = 1e9, 'bi'
    elif a >= 1e6:
        base, unid = 1e6, 'mi'
    elif a >= 1e3:
        base, unid = 1e3, 'mil'
    else:
        base, unid = 1, ''
    num = f'{a/base:,.{decimais}f}'.replace(',', 'T').replace('.', ',').replace('T', '.')
    return f'{"-" if valor < 0 else ""}R$ {num} {unid}'.strip()


def formatar_percentual(v):
    return 'N/D' if pd.isna(v) else f'{v:.2f}%'.replace('.', ',')


def resumo_executivo(linha, ano, cenario_rotulo, meta=None):
    checagem = conferir_caixa(linha)
    linhas = [
        '# CTI — Resumo executivo',
        f'**Recorte:** {cenario_rotulo}, Ano simulado {ano}.',
        '**Moeda de apresentação:** R$ por convenção do projeto; fonte não explicita moeda.',
        '', '## Indicadores da DRE',
        f'- Receita: {formatar_moeda(linha.receita)}',
        f'- Resultado operacional: {formatar_moeda(linha.resultado_operacional)}',
        f'- Lucro líquido: {formatar_moeda(linha.lucro_liquido)}',
        f'- Margem operacional: {formatar_percentual(linha.margem_operacional_pct)}',
        '', '## Fluxo de caixa',
        f'- Saldo inicial: {formatar_moeda(linha.saldo_inicial_caixa)}',
        f'- Geração líquida no período: {formatar_moeda(linha.geracao_caixa)}',
        f'- Saldo final: {formatar_moeda(linha.saldo_final_caixa)}',
        f'- Reconciliação: {"confere" if checagem["ok"] else "requer verificação"}',
        '', '## Pontos de atenção (regras automáticas)',
    ]
    for nivel, titulo, detalhe in alertas(linha, meta):
        linhas.append(f'- **{titulo}:** {detalhe}')
    linhas += ['', '## Limitações',
               '- Cenários alternativos, não observações de exercícios financeiros reais.',
               '- Análise descritiva, não comprovação de causalidade nem parecer contábil.',
               '- Sem setor da concessão, moeda oficial ou metas oficiais informadas.',
               '- EBITDA foi utilizado conforme a conta original da DRE.',
               '- Indicadores de média entre cenários são médias simples, não ponderadas.']
    return '\n'.join(linhas)
