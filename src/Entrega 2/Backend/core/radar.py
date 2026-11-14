"""Radar descritivo de cenários financeiros.

Não atribui probabilidades, graus de risco ou recomendações de investimento.
Classificação por dois critérios auditáveis: geração líquida de caixa e
margem operacional em relação a uma referência explicitada ao usuário.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

CATEGORIAS = (
    "Margem ≥ referência · Caixa não negativo",
    "Margem < referência · Caixa não negativo",
    "Margem ≥ referência · Caixa negativo",
    "Margem < referência · Caixa negativo",
)

CORES_CATEGORIAS = {
    CATEGORIAS[0]: "#39C7AE",  # verde
    CATEGORIAS[1]: "#79A9EC",  # azul
    CATEGORIAS[2]: "#EDBA6C",  # amarelo
    CATEGORIAS[3]: "#F0717D",  # vermelho
}

CAMPOS_RADAR = (
    "ano", "cenario", "margem_operacional_pct", "geracao_caixa",
    "receita", "resultado_operacional", "lucro_liquido", "saldo_final_caixa",
)


def preparar_radar(base: pd.DataFrame, ano: int, referencia: float | None = None):
    """Devolve os cenários completos do ano, sem aplicar a seleção lateral.

    Se referencia=None, usa mediana da margem operacional dos cenários
    completos do ano. Valores ausentes são excluídos, nunca imputados por 0.
    """
    faltantes = set(CAMPOS_RADAR).difference(base.columns)
    if faltantes:
        raise ValueError(f"Campos ausentes na base do Radar: {', '.join(sorted(faltantes))}")

    dados = base.loc[base["ano"] == ano, list(CAMPOS_RADAR)].copy()
    if dados.empty:
        return dados.assign(grupo=pd.Series(dtype="object")), np.nan, 0
    if dados.duplicated(["ano", "cenario"]).any():
        raise ValueError(f"Há cenários duplicados para o Ano {ano}.")

    # Valores inválidos nos dois eixos não geram pontos ou diagnósticos.
    for campo in ("margem_operacional_pct", "geracao_caixa"):
        dados[campo] = pd.to_numeric(dados[campo], errors="coerce")
        dados[campo] = dados[campo].replace([np.inf, -np.inf], np.nan)
    n_invalidos = int(dados[["margem_operacional_pct", "geracao_caixa"]].isna().any(axis=1).sum())
    dados = dados.dropna(subset=["margem_operacional_pct", "geracao_caixa"]).copy()
    if dados.empty:
        return dados.assign(grupo=pd.Series(dtype="object")), np.nan, n_invalidos

    limite = float(dados["margem_operacional_pct"].median() if referencia is None else referencia)
    if not np.isfinite(limite):
        raise ValueError("A referência de margem deve ser um número finito.")

    margem_alta = dados["margem_operacional_pct"] >= limite
    caixa_ok = dados["geracao_caixa"] >= 0
    dados["grupo"] = np.select(
        [margem_alta & caixa_ok, ~margem_alta & caixa_ok,
         margem_alta & ~caixa_ok, ~margem_alta & ~caixa_ok],
        CATEGORIAS, default=CATEGORIAS[3],
    )
    dados["geracao_caixa_bi"] = dados["geracao_caixa"] / 1e9
    return dados.sort_values("cenario").reset_index(drop=True), limite, n_invalidos


def resumo_radar(dados: pd.DataFrame):
    """Contagens simples, com cada cenário contado apenas uma vez."""
    grupos = dados["grupo"].value_counts() if "grupo" in dados else pd.Series(dtype=int)
    return {
        "total": len(dados),
        "caixa_negativo": int((dados["geracao_caixa"] < 0).sum()),
        "por_grupo": {nome: int(grupos.get(nome, 0)) for nome in CATEGORIAS},
    }


def diagnostico_cenario(registro: pd.Series, referencia: float):
    """Interpretação textual baseada apenas nas duas dimensões do Radar."""
    margem = float(registro["margem_operacional_pct"])
    caixa = float(registro["geracao_caixa"])
    if caixa < 0 and margem >= referencia:
        return (
            "A margem operacional está no patamar de referência ou acima, "
            "mas a geração líquida de caixa é negativa. Resultado operacional e "
            "movimentação de caixa contam histórias diferentes neste período."
        )
    if caixa < 0 and margem < referencia:
        return (
            "A margem operacional está abaixo da referência e a geração líquida "
            "de caixa é negativa. Vale examinar custos, investimentos e demais "
            "componentes do fluxo de caixa deste cenário."
        )
    if caixa >= 0 and margem < referencia:
        return (
            "A geração líquida de caixa não é negativa, mas a margem operacional "
            "está abaixo da referência definida. Vale investigar a composição "
            "do resultado operacional."
        )
    return (
        "O cenário apresenta geração líquida de caixa não negativa e margem "
        "operacional no patamar de referência ou acima. Isso descreve apenas "
        "os dois indicadores selecionados, sem comprovar viabilidade financeira."
    )
