"""Testes de qualidade e comparação integral da base analítica com o CSV original.

Execute da raiz: python scripts/validar_dados.py
Um relatório em Markdown será produzido em relatorios/validacao_dados.md.
"""
from pathlib import Path
import sys
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.preparar_dados import CONTAS, COMPONENTES_CAIXA, numero_br

ORIGINAL = ROOT / 'dados' / 'Demonstrativo Fecap v3.csv'
PROCESSADO = ROOT / 'dados' / 'indicadores_cti.csv'
RELATORIO = ROOT / 'relatorios' / 'validacao_dados.md'


def executar():
    tabela = pd.read_csv(PROCESSADO, encoding='utf-8-sig')
    bruto = pd.read_csv(ORIGINAL, sep=';', encoding='latin-1', header=None,
                        names=['ano','cenario','conta','valor'], dtype=str, keep_default_na=False)
    orig = bruto.loc[bruto['conta'].isin(CONTAS)].copy()
    orig['ano'] = orig.ano.str.extract(r'(\d+)')[0].astype(int)
    orig['cenario'] = orig.cenario.str.extract(r'(\d+)')[0].astype(int)
    orig['valor'] = numero_br(orig.valor)
    recomparar = orig.pivot(index=['ano','cenario'], columns='conta', values='valor').rename(columns=CONTAS).reset_index()
    merged = tabela.merge(recomparar, on=['ano','cenario'], suffixes=('_processada', '_original'), validate='one_to_one')

    resultados = {}
    resultados['Registros de cenários/anos (14.400)'] = len(tabela) == 14_400
    resultados['1.200 cenários'] = tabela['cenario'].nunique() == 1200
    resultados['12 anos'] = tabela['ano'].nunique() == 12
    resultados['Sem pares duplicados'] = not tabela.duplicated(['ano','cenario']).any()
    resultados['Sem contas obrigatórias vazias'] = not tabela[list(CONTAS.values())].isna().any().any()
    resultados['100% das contas preservadas frente ao original'] = len(merged) == len(tabela)

    max_diferenca_origem = 0.0
    for coluna in CONTAS.values():
        diff = (merged[f'{coluna}_processada'] - merged[f'{coluna}_original']).abs().max()
        max_diferenca_origem = max(max_diferenca_origem, float(diff))
    resultados['Comparação integral com CSV original (erro < R$ 0,01)'] = max_diferenca_origem < 0.01

    for nome, num in [('Margem operacional', 'resultado_operacional'),
                      ('Margem líquida', 'lucro_liquido'), ('Margem EBITDA', 'ebitda')]:
        coluna = {'Margem operacional':'margem_operacional_pct',
                  'Margem líquida':'margem_liquida_pct',
                  'Margem EBITDA':'margem_ebitda_pct'}[nome]
        esperado = tabela[num] / tabela['receita'].where(tabela['receita'] != 0) * 100
        resultados[f'Fórmula de {nome.lower()}'] = bool(np.allclose(
            esperado, tabela[coluna], rtol=1e-10, atol=1e-8, equal_nan=True))

    dif_fluxo = (tabela[COMPONENTES_CAIXA].sum(axis=1) - tabela['geracao_caixa']).abs()
    dif_saldo = (tabela['saldo_inicial_caixa'] + tabela['geracao_caixa'] - tabela['saldo_final_caixa']).abs()
    dif_financeiro = (tabela['entradas_financeiras_caixa'] + tabela['despesas_financeiras_caixa'] - tabela['resultado_financeiro_caixa']).abs()
    dif_dre = (tabela[['receita','tributos_dre','custos_dre','depreciacao_amortizacao_dre']].sum(axis=1) - tabela['resultado_operacional']).abs()
    dif_bal = (tabela['ativo_total'] + tabela['passivo_total']).abs()
    resultados['Reconciliação FLU componentes vs geração (R$ 0,01)'] = bool((dif_fluxo < .01).all())
    resultados['Reconciliação FLU saldo inicial + geração = final (R$ 0,01)'] = bool((dif_saldo < .01).all())
    resultados['Resultado financeiro = entradas + despesas financeiras (R$ 0,01)'] = bool((dif_financeiro < .01).all())
    resultados['DRE resultado operacional = receita + tributos + custos + D&A (R$ 0,01)'] = bool((dif_dre < .01).all())
    # Há resíduo na fonte (aprox. 2,5 centavos) entre total do ativo e do passivo.
    resultados['BAL ativo + passivo (tolerância R$ 0,10)'] = bool((dif_bal < .10).all())

    cont_ativo_neg = int((tabela['ativo_total'] < 0).sum())
    cont_caixa_neg_12 = int(((tabela['ano'] == 12) & (tabela['geracao_caixa'] < 0)).sum())
    relatorio = [
        '# CTI — Relatório de Validação da Base Financeira',
        '', '## Escopo',
        f'- Fonte: `{ORIGINAL.name}` (preservada); base tratada: `{PROCESSADO.name}`.',
        f'- {len(tabela):,} registros de pares ano/cenário.',
        f'- {tabela.cenario.nunique()} cenários; {tabela.ano.nunique()} anos simulados.',
        f'- {len(CONTAS)} contas financeiras comparadas com a fonte linha a linha.',
        '- Valores monetários exibidos como R$ por convenção de apresentação.',
        '', '## Testes automatizados',
    ]
    for teste, passou in resultados.items():
        relatorio.append(f'- **{"APROVADO" if passou else "FALHOU"}** — {teste}')
    relatorio += [
        '', '## Diferenças máximas observadas (valores absolutos na unidade original)',
        f'- Processo versus fonte: {max_diferenca_origem:.8f}',
        f'- Ponte do fluxo versus geração: {dif_fluxo.max():.8f}',
        f'- Saldo inicial + geração versus saldo final: {dif_saldo.max():.8f}',
        f'- Financeiro: {dif_financeiro.max():.8f}',
        f'- DRE: {dif_dre.max():.8f}',
        f'- Balanço, ativo + passivo: {dif_bal.max():.8f}',
        '', '## Pontos de atenção para os analistas da CTI',
        f'- O conjunto possui {cont_ativo_neg} registros com ativo total negativo. A origem foi preservada; a interpretação precisa de confirmação.',
        f'- No Ano 12, {cont_caixa_neg_12} de 1.200 cenários têm geração líquida de caixa negativa (não é probabilidade de risco).',
        '- A fonte não confirma setor, moeda, metas financeiras nem probabilidade dos cenários.',
        '- Contas do balanço apresentam sinal contábil na fonte; não se ajustaram os sinais.',
        '- EBITDA foi extraído do demonstrativo; não foi substituído por fórmula própria.',
        '- A tolerância para o balanço difere da do fluxo porque a fonte já possui diferença residual de cerca de R$ 0,025.',
        '', '## Conclusão',
        '**As verificações matemáticas atestam a fidelidade ao arquivo recebido, não a adequação das premissas contábeis do modelo de concessão.**',
    ]
    RELATORIO.parent.mkdir(parents=True, exist_ok=True)
    RELATORIO.write_text('\n'.join(relatorio) + '\n', encoding='utf-8')
    print('\n'.join(relatorio))
    if not all(resultados.values()):
        raise SystemExit('Há testes reprovados. Verifique a fonte e as regras antes da entrega.')
    return resultados


if __name__ == '__main__':
    executar()
