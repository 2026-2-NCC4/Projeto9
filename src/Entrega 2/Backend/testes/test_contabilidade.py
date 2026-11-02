"""Verificações de integração planilha ↔ interface ↔ base CTI."""
import unittest
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.contabilidade import (
    INDICADORES, agregar_por_ano, calcular_mva, carregar_dicionario,
    carregar_planilha_convertida, carregar_ranking, formatar_kpi,
    ano_mais_recente_com_liquidez,
)


class TestPlanilhaContabilidade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = carregar_planilha_convertida()
        cls.rank = carregar_ranking()

    def test_matriz_completa(self):
        self.assertEqual(len(self.df), 14400)
        self.assertEqual(self.df['cenario'].nunique(), 1200)
        self.assertEqual(self.df['ano'].nunique(), 12)
        self.assertEqual(len(INDICADORES), 25)
        self.assertEqual(len(carregar_dicionario()), 25)

    def test_numeros_originais_conferidos_com_planilha(self):
        row = self.df.query('ano==1 and cenario==1').iloc[0]
        self.assertAlmostEqual(row.lc, 2.22566030274245, places=11)
        self.assertAlmostEqual(row.eg, 0.810985721563656, places=11)
        self.assertAlmostEqual(row.marg_ebitda, 0.829972906828987, places=11)
        self.assertAlmostEqual(row.eva, 1978868441.99604, delta=0.01)
        self.assertAlmostEqual(row.capital_investido, 7942794236.89870, delta=0.01)

    def test_mva_reproduz_aba_ranking(self):
        by_scenario = self.rank.set_index('cenario')['mva_planilha']
        for cid in (1, 4, 300, 900, 1088, 1200):
            mva = calcular_mva(self.df, [cid], 0.105)
            self.assertAlmostEqual(mva, by_scenario.loc[cid], delta=0.01)

    def test_wacc_afeta_apenas_eva_e_mva(self):
        all1 = self.df[self.df.cenario.isin([1,2,3])]
        a = agregar_por_ano(all1, .105)
        b = agregar_por_ano(all1, .125)
        self.assertAlmostEqual(a.loc[0,'lc'], b.loc[0,'lc'], places=12)
        self.assertNotAlmostEqual(a.loc[0,'eva'], b.loc[0,'eva'], delta=1)
        self.assertNotAlmostEqual(calcular_mva(self.df,[1], .105), calcular_mva(self.df,[1],.125), delta=1)

    def test_medias_recalculam_razoes(self):
        multi = self.df[(self.df.cenario.isin([1,2,3])) & (self.df.ano==1)]
        registro = agregar_por_ano(multi).iloc[0]
        self.assertAlmostEqual(registro['lc'], multi['ativo_circulante_aj'].mean()/multi['passivo_circulante_aj'].mean(), places=12)
        self.assertAlmostEqual(registro['eg'], multi['capital_terceiros'].mean()/multi['ativo_total_aj'].mean(), places=12)
        self.assertAlmostEqual(registro['marg_ebitda'], multi['ebitda_informado_planilha'].mean()/multi['receita_liquida_planilha'].mean(), places=12)

    def test_ano_padrao_com_liquidez(self):
        # Filtro padrão de 1 a 12: Ano 11 é o último com seis KPIs disponíveis.
        todos = agregar_por_ano(self.df.query('cenario == 1'))
        self.assertEqual(ano_mais_recente_com_liquidez(todos), 11)
        # Se o usuário reduzir o intervalo, respeitamos o último ano do filtro.
        ate_oito = todos[todos.ano.between(2, 8)]
        self.assertEqual(ano_mais_recente_com_liquidez(ate_oito), 8)
        # Ano 12 continua acessível, com N/D explícito.
        so_doze = todos[todos.ano == 12]
        self.assertEqual(ano_mais_recente_com_liquidez(so_doze), 12)
        self.assertTrue(so_doze[['lc', 'ls', 'li', 'lg', 'ccl', 'icc']].isna().all().all())

    def test_n_d_no_ano_12(self):
        self.assertTrue(self.df.query('ano==12').lc.isna().all())
        self.assertTrue(self.df.query('ano==12').eg.isna().all())
        self.assertEqual(formatar_kpi(np.nan, 'x'), 'N/D')
        self.assertTrue(self.df.query('ano==12').eva.notna().all())

    def test_nunca_soma_cenarios_alternativos(self):
        ids = [1,2,3]
        medio = calcular_mva(self.df, ids, .105)
        esperado = np.mean([calcular_mva(self.df, [i],.105) for i in ids])
        self.assertAlmostEqual(medio, esperado, delta=0.01)


if __name__ == '__main__':
    unittest.main()
