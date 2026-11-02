"""Extrai valores *já calculados* na planilha da Entrega 1 para uso no Streamlit.

Não altera a planilha, nem tenta reinterpretar suas reclassificações contábeis.
Requer apenas a biblioteca-padrão do Python. Executar na raiz do projeto:
    python scripts/importar_planilha_contabilidade.py
O .xlsx original deve estar em referencias/ (ver README).
"""
from pathlib import Path
import csv
import json
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'referencias' / 'PI_Entrega01_Contabilidade_e_Financas.xlsx'
DEST = ROOT / 'dados' / 'kpis_contabilidade.csv'
RANK_DEST = ROOT / 'dados' / 'ranking_contabilidade.csv'
META_DEST = ROOT / 'relatorios' / 'dicionario_kpis_planilha.json'
N = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'

FIELDS = [
    'cenario', 'ano', 'ano_num', 'ativo_circulante_aj', 'estoques_planilha', 'disponivel_planilha',
    'realizavel_lp', 'passivo_circulante_aj', 'exigivel_lp_aj', 'divida_onerosa',
    'patrimonio_liquido_planilha', 'permanente', 'ativo_total_aj', 'capital_terceiros',
    'divida_liquida', 'receita_liquida_planilha', 'custos_planilha', 'ebitda_informado_planilha',
    'ebitda_recalculado', 'ebit', 'depreciacao_planilha', 'despesas_financeiras', 'lair',
    'lucro_liquido_planilha', 'geracao_caixa_planilha', 'aliquota_efetiva', 'nopat',
    'capital_investido', 'capital_investido_abertura', 'lc', 'ls', 'li', 'lg', 'ccl', 'icc',
    'eg', 'pct', 'ce', 'ipl', 'irnc', 'gef', 'dle', 'icj', 'maf', 'marg_ebitda',
    'marg_liquida', 'roe', 'roa', 'eva', 'flag_pl_negativo', 'flag_ci_negativo',
    'flag_pc_nao_concilia', 'flag_sem_balanco',
]
RANK_FIELDS = ['cenario', 'posicao', 'score', 'pilar_mais_forte', 'pilar_limitante',
               'pilar_valor', 'pilar_rentabilidade', 'pilar_liquidez', 'pilar_endividamento',
               'mva_planilha']


def col_index(ref):
    letters = re.match(r'[A-Z]+', ref).group(0)
    i = 0
    for c in letters:
        i = i * 26 + ord(c) - ord('A') + 1
    return i - 1


def rows(archive, name, shared):
    with archive.open(name) as file:
        for event, element in ET.iterparse(file, events=('end',)):
            if element.tag != N + 'row':
                continue
            row_number = int(element.attrib['r'])
            data = {}
            for cell in element.findall(N + 'c'):
                value_el = cell.find(N + 'v')
                if value_el is None or value_el.text is None:
                    continue
                value = value_el.text
                if cell.attrib.get('t') == 's':
                    value = shared[int(value)]
                data[col_index(cell.attrib['r'])] = value
            yield row_number, data
            element.clear()


def parse_number(value):
    if value is None or value in ('', '–', '-', 'N/D', 'None'):
        return ''
    try:
        return float(value)
    except (ValueError, TypeError):
        return value


def main():
    if not SOURCE.is_file():
        raise FileNotFoundError(f'Planilha original não encontrada: {SOURCE}')
    DEST.parent.mkdir(parents=True, exist_ok=True)
    META_DEST.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(SOURCE) as archive:
        strings_root = ET.fromstring(archive.read('xl/sharedStrings.xml'))
        strings = [''.join(t.text or '' for t in si.findall('.//' + N + 't'))
                   for si in strings_root.findall(N + 'si')]
        metadata = []
        for number, cells in rows(archive, 'xl/worksheets/sheet1.xml', strings):
            if 5 <= number <= 29:
                metadata.append({
                    'id': cells.get(0, ''), 'nome': cells.get(1, ''),
                    'categoria': cells.get(2, ''), 'objetivo': cells.get(3, ''),
                    'formula': cells.get(4, ''), 'unidade': cells.get(5, ''),
                    'fonte': cells.get(6, ''), 'validacao': cells.get(9, ''),
                    'interpretacao': cells.get(10, ''),
                })
        META_DEST.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
        count = 0
        with DEST.open('w', newline='', encoding='utf-8') as fp:
            writer = csv.writer(fp)
            writer.writerow(FIELDS)
            for row_number, cells in rows(archive, 'xl/worksheets/sheet5.xml', strings):
                if row_number < 5:
                    continue
                cenario = cells.get(0, '')
                if not cenario.startswith('Cenário '):
                    continue
                row = []
                for i in range(len(FIELDS)):
                    raw = cells.get(i, '')
                    if i == 0:
                        raw = int(raw.split()[-1])
                    elif i == 1:
                        raw = int(raw.split()[-1])
                    elif i == 2:
                        raw = int(float(raw))
                    elif i < 49:
                        raw = parse_number(raw)
                    row.append(raw)
                writer.writerow(row)
                count += 1
        count_rank = 0
        with RANK_DEST.open('w', newline='', encoding='utf-8') as fp:
            writer = csv.writer(fp)
            writer.writerow(RANK_FIELDS)
            for row_number, cells in rows(archive, 'xl/worksheets/sheet7.xml', strings):
                if row_number < 24 or row_number > 1223:
                    continue
                cenario = cells.get(0, '')
                if not cenario.startswith('Cenário '):
                    continue
                row = [int(cenario.split()[-1])]
                for i in range(1, len(RANK_FIELDS)):
                    v = cells.get(i, '')
                    if i not in (3,4):
                        v = parse_number(v)
                    row.append(v)
                writer.writerow(row)
                count_rank += 1
    if count != 14400 or count_rank != 1200 or len(metadata) != 25:
        raise ValueError(f'Extração incompleta: registros={count}, ranking={count_rank}, KPIs={len(metadata)}')
    print(f'OK | {count:,} linhas e 25 KPIs da planilha; ranking={count_rank:,} cenários')
    print(f'Arquivos: {DEST}, {RANK_DEST}, {META_DEST}')


if __name__ == '__main__':
    main()
