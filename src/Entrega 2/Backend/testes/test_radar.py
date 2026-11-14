"""Testes do Radar; executar com unittest discover na pasta Backend/testes."""
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from core.radar import CATEGORIAS, preparar_radar, resumo_radar, diagnostico_cenario


class TestRadar(unittest.TestCase):
    def setUp(self):
        self.exemplo = pd.DataFrame({
            "ano": [1] * 4 + [2],
            "cenario": [1, 2, 3, 4, 1],
            "margem_operacional_pct": [30, 10, 30, 10, 1],
            "geracao_caixa": [1e9, 1e9, -1e9, -1e9, -1e9],
            "receita": [5e9] * 5,
            "resultado_operacional": [2e9] * 5,
            "lucro_liquido": [1e9] * 5,
            "saldo_final_caixa": [1e9] * 5,
        })

    def test_quatro_combinacoes(self):
        dados, limite, invalidos = preparar_radar(self.exemplo, 1, 20)
        self.assertEqual(limite, 20)
        self.assertEqual(invalidos, 0)
        self.assertEqual(dados["grupo"].tolist(), list(CATEGORIAS))
        resumo = resumo_radar(dados)
        self.assertEqual(resumo["total"], 4)
        self.assertEqual(resumo["caixa_negativo"], 2)
        self.assertTrue(all(resumo["por_grupo"][g] == 1 for g in CATEGORIAS))

    def test_mediana_no_ano_e_filtragem(self):
        dados, limite, _ = preparar_radar(self.exemplo, 1)
        self.assertEqual(limite, 20)
        self.assertEqual(len(dados), 4)
        self.assertTrue((dados.ano == 1).all())

    def test_zero_e_referencia_inclusiva(self):
        x = self.exemplo.iloc[[0]].copy()
        x.loc[:, "margem_operacional_pct"] = 20
        x.loc[:, "geracao_caixa"] = 0
        dados, _, _ = preparar_radar(x, 1, 20)
        self.assertEqual(dados.iloc[0]["grupo"], CATEGORIAS[0])

    def test_descarta_invalidos_sem_imputar(self):
        x = self.exemplo.copy()
        x.loc[0, "geracao_caixa"] = np.nan
        dados, _, invalidos = preparar_radar(x, 1, 20)
        self.assertEqual(invalidos, 1)
        self.assertEqual(len(dados), 3)
        self.assertNotIn(1, dados["cenario"].tolist())

    def test_nao_altera_base(self):
        x = self.exemplo.copy(deep=True)
        preparar_radar(x, 1)
        pd.testing.assert_frame_equal(x, self.exemplo)

    def test_diagnostico_distinto_para_caixa_negativo(self):
        dados, limite, _ = preparar_radar(self.exemplo, 1, 20)
        texto = diagnostico_cenario(dados.iloc[2], limite)
        self.assertIn("geração líquida de caixa é negativa", texto)

    def test_duplicidade_invalida(self):
        x = pd.concat([self.exemplo, self.exemplo.iloc[[0]]], ignore_index=True)
        with self.assertRaises(ValueError):
            preparar_radar(x, 1)

    def test_base_real_1200_por_ano(self):
        base = pd.read_csv(BACKEND / "dados" / "indicadores_cti.csv")
        ano11, limite11, invalidos11 = preparar_radar(base, 11)
        ano12, limite12, invalidos12 = preparar_radar(base, 12)
        self.assertEqual(len(ano11), 1200)
        self.assertEqual(len(ano12), 1200)
        self.assertEqual(invalidos11 + invalidos12, 0)
        self.assertEqual(resumo_radar(ano11)["caixa_negativo"], 0)
        self.assertEqual(resumo_radar(ano12)["caixa_negativo"], 1170)
        self.assertGreater(limite12, limite11)


if __name__ == "__main__":
    unittest.main()
