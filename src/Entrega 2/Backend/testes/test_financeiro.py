"""Testes rápidos das regras de negócio, separados da interface Streamlit."""
import sys
from pathlib import Path
import unittest

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.analise import media_cenarios, conferir_caixa, alertas, regressao_temporal, formatar_moeda


class TestFinanceiro(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = pd.read_csv(ROOT / 'dados' / 'indicadores_cti.csv')

    def test_base_tem_granularidade_unica(self):
        self.assertEqual(len(self.base), 14400)
        self.assertEqual(self.base.cenario.nunique(), 1200)
        self.assertFalse(self.base.duplicated(['ano','cenario']).any())

    def test_reconciliacao_caixa_ano_12_cenario_1(self):
        linha = self.base.query('ano == 12 and cenario == 1').iloc[0]
        self.assertTrue(conferir_caixa(linha)['ok'])
        self.assertAlmostEqual(float(linha.receita), 12222538183.3716, places=2)
        self.assertAlmostEqual(float(linha.lucro_liquido), 7093819432.34778, places=2)

    def test_reconciliacao_toda_base(self):
        self.assertLess(float(self.base.diferenca_geracao_caixa.abs().max()), .01)
        self.assertLess(float(self.base.diferenca_saldo_caixa.abs().max()), .01)

    def test_media_recalcula_margem_entre_cenarios(self):
        linhas = self.base.query('ano == 12 and cenario in [1,2,3]')
        media = media_cenarios(linhas).iloc[0]
        esperado = 100 * linhas.resultado_operacional.mean() / linhas.receita.mean()
        self.assertAlmostEqual(media.margem_operacional_pct, esperado, places=8)
        self.assertAlmostEqual(media.geracao_caixa, linhas.geracao_caixa.mean(), places=4)

    def test_alerta_de_caixa_e_lucro(self):
        linha = self.base.query('ano == 12 and cenario == 1').iloc[0]
        self.assertIn('Lucro positivo e caixa líquido negativo',
                      [t for _,t,_ in alertas(linha)])

    def test_regressao_nao_extrapola(self):
        serie = self.base.query('cenario == 1')
        resposta = regressao_temporal(serie, 'receita')
        self.assertEqual(resposta['n'], 12)
        self.assertEqual(len(resposta['tabela']), 12)
        self.assertTrue(np.isfinite(resposta['coeficiente_ano']))

    def test_moeda(self):
        self.assertEqual(formatar_moeda(-2_827_614_976.451), '-R$ 2,83 bi')


if __name__ == '__main__':
    unittest.main()
