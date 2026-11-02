"""DashBird - Entrega 2: regressão financeira reproduzível.

Uso a partir da pasta CTI_Entrega2:
  python caminho/para/analise_regressao.py --dados dados/indicadores_cti.csv --saida resultados_regressao

A análise principal utiliza Anos 1-11: o Ano 12 tem menos contas
contábeis na fonte e é mantido como análise de sensibilidade.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import jarque_bera
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

NECESSARIAS = {"ano", "cenario", "lucro_liquido", "geracao_caixa"}


def processar(dados: Path, saida: Path) -> dict:
    if not dados.is_file():
        raise FileNotFoundError(f"Base processada não encontrada: {dados}")
    saida.mkdir(parents=True, exist_ok=True)
    base = pd.read_csv(dados)
    ausentes = NECESSARIAS.difference(base.columns)
    if ausentes:
        raise ValueError(f"Colunas obrigatórias ausentes: {sorted(ausentes)}")
    if base[list(NECESSARIAS)].isna().any().any():
        raise ValueError("Há valores ausentes em colunas essenciais")
    if base.duplicated(["ano", "cenario"]).any():
        raise ValueError("Há pares ano/cenário duplicados")
    if not np.isfinite(base[["lucro_liquido", "geracao_caixa"]].to_numpy()).all():
        raise ValueError("Há valores monetários não finitos")
    base = base.copy()
    base["lucro_bi"] = base["lucro_liquido"] / 1e9
    base["caixa_bi"] = base["geracao_caixa"] / 1e9
    base["ano"] = base["ano"].astype(int)
    base["cenario"] = base["cenario"].astype(int)
    anos = sorted(base["ano"].unique().tolist())
    if anos != list(range(1, 13)):
        raise ValueError(f"Anos inesperados na base: {anos}")

    # Pré-definido pelas diferenças de estrutura contábil já vistas na Entrega 1.
    principal = base.loc[base.ano.between(1, 11)].copy()
    term = base.loc[base.ano.eq(12)].copy()
    ids = np.sort(principal.cenario.unique())
    treino_ids, teste_ids = train_test_split(ids, test_size=0.20, random_state=42)
    treino = principal[principal.cenario.isin(treino_ids)].copy()
    teste = principal[principal.cenario.isin(teste_ids)].copy()

    formula_baseline = "caixa_bi ~ C(ano)"
    formula_principal = "caixa_bi ~ lucro_bi + C(ano)"
    modelo_baseline = smf.ols(formula_baseline, treino).fit()
    modelo = smf.ols(formula_principal, treino).fit(
        cov_type="cluster", cov_kwds={"groups": treino.cenario}
    )
    # Diagnóstico alternativo; a variação de sensibilidade não substitui o modelo principal.
    modelo_heterogeneo = smf.ols("caixa_bi ~ lucro_bi * C(ano)", treino).fit()

    def metricas(modelo_: object) -> dict:
        predito = modelo_.predict(teste)
        return {
            "r2_teste": float(r2_score(teste.caixa_bi, predito)),
            "mae_teste_bi": float(mean_absolute_error(teste.caixa_bi, predito)),
            "rmse_teste_bi": float(np.sqrt(mean_squared_error(teste.caixa_bi, predito))),
            "r2_treino": float(modelo_.rsquared),
        }

    mp = metricas(modelo)
    mb = metricas(modelo_baseline)
    mh = metricas(modelo_heterogeneo)
    bptest = het_breuschpagan(modelo.resid, modelo.model.exog)
    jb = jarque_bera(modelo.resid)
    corrs = base.groupby("ano", sort=True).apply(
        lambda d: d["lucro_bi"].corr(d["caixa_bi"]), include_groups=False
    )
    modelo_todos = smf.ols("caixa_bi ~ lucro_bi + C(ano)", base).fit()
    modelo_ano12 = smf.ols("caixa_bi ~ lucro_bi", term).fit()
    medias = principal.groupby("ano", as_index=False)[["lucro_bi", "caixa_bi"]].mean()

    previsao = teste[["ano", "cenario", "lucro_bi", "caixa_bi"]].copy()
    previsao["caixa_predito_bi"] = modelo.predict(teste)
    previsao["residuo_bi"] = previsao.caixa_bi - previsao.caixa_predito_bi
    previsao.to_csv(saida / "previsoes_teste.csv", index=False, encoding="utf-8-sig")
    medias.to_csv(saida / "medias_por_ano.csv", index=False, encoding="utf-8-sig")

    # Figura 1: médias de cada ano do conjunto principal.
    plt.figure(figsize=(9, 4.8))
    plt.plot(medias.ano, medias.lucro_bi, marker="o", label="Lucro líquido")
    plt.plot(medias.ano, medias.caixa_bi, marker="s", label="Geração de caixa")
    plt.xlabel("Ano simulado")
    plt.ylabel("Bilhões de unidades monetárias")
    plt.title("Evolução média por ano - 1.200 cenários")
    plt.xticks(medias.ano)
    plt.legend()
    plt.grid(alpha=0.20)
    plt.tight_layout()
    plt.savefig(saida / "01_evolucao_medias.png", dpi=180)
    plt.close()

    # Figura 2: comparação no conjunto de cenários nunca usado no ajuste.
    amostra = previsao.sample(n=min(2000, len(previsao)), random_state=42)
    plt.figure(figsize=(6.8, 5.2))
    plt.scatter(amostra.caixa_predito_bi, amostra.caixa_bi, s=7, alpha=0.28)
    alcance = [min(amostra.caixa_predito_bi.min(), amostra.caixa_bi.min()),
               max(amostra.caixa_predito_bi.max(), amostra.caixa_bi.max())]
    plt.plot(alcance, alcance, linestyle="--", linewidth=1, label="Predição perfeita")
    plt.xlabel("Geração de caixa predita (bilhões)")
    plt.ylabel("Geração de caixa observada (bilhões)")
    plt.title("Validação fora da amostra - cenários reservados")
    plt.grid(alpha=0.20)
    plt.legend()
    plt.tight_layout()
    plt.savefig(saida / "02_observado_vs_predito.png", dpi=180)
    plt.close()

    # Figura 3: avaliação visual de padrão nos resíduos.
    plt.figure(figsize=(7.2, 4.8))
    plt.scatter(amostra.caixa_predito_bi, amostra.residuo_bi, s=7, alpha=0.28)
    plt.axhline(0, linestyle="--", linewidth=1)
    plt.xlabel("Geração de caixa predita (bilhões)")
    plt.ylabel("Resíduo (bilhões)")
    plt.title("Resíduos - cenários reservados")
    plt.grid(alpha=0.20)
    plt.tight_layout()
    plt.savefig(saida / "03_residuos.png", dpi=180)
    plt.close()

    plt.figure(figsize=(9.4, 4.8))
    plt.bar(corrs.index.astype(str), corrs.to_numpy())
    plt.axhline(0, linewidth=1)
    plt.xlabel("Ano simulado")
    plt.ylabel("Correlação de Pearson")
    plt.title("Relação lucro-caixa varia entre os anos (Ano 12: análise complementar)")
    plt.ylim(-1, 1)
    plt.grid(axis="y", alpha=0.20)
    plt.tight_layout()
    plt.savefig(saida / "04_correlacao_por_ano.png", dpi=180)
    plt.close()

    resumo = {
        "fonte": str(dados),
        "unidade": "bilhões de unidades monetárias; moeda original a confirmar",
        "base_n": int(len(base)),
        "n_cenarios": int(base.cenario.nunique()),
        "anos_base": anos,
        "anos_modelagem": [1, 11],
        "justificativa_exclusao_ano12": "Ano 12 possui estrutura contábil reduzida na fonte: 42 contas versus 68/69 nos anos anteriores.",
        "treino_n": len(treino), "teste_n": len(teste),
        "treino_cenarios": len(treino_ids), "teste_cenarios": len(teste_ids),
        "modelo": formula_principal,
        "beta_lucro": float(modelo.params["lucro_bi"]),
        "beta_intervalo_confianca_95": [float(x) for x in modelo.conf_int().loc["lucro_bi"]],
        "beta_p_valor_robusto_cluster": float(modelo.pvalues["lucro_bi"]),
        "beta_erro_padrao_robusto_cluster": float(modelo.bse["lucro_bi"]),
        "r2_ajustado_treino": float(modelo.rsquared_adj),
        "principal": mp, "baseline_ano": mb, "interacao_ano": mh,
        "heterocedasticidade_breusch_pagan_pvalor": float(bptest[1]),
        "normalidade_jarque_bera_pvalor": float(jb[1]),
        "desvio_residuos_teste_bi": float(previsao.residuo_bi.std(ddof=1)),
        "correlacao_por_ano": {str(k): float(v) for k,v in corrs.items()},
        "sensibilidade_beta_todos_anos": float(modelo_todos.params["lucro_bi"]),
        "sensibilidade_beta_ano12": float(modelo_ano12.params["lucro_bi"]),
        "medias_por_ano": medias.to_dict(orient="records"),
        "coeficientes": {k:float(v) for k,v in modelo.params.items()},
        "metodo_validacao": "Separação 80/20 por identificador de cenário, random_state=42; erros padrão clusterizados por cenário no treino.",
    }
    (saida / "resumo_resultados.json").write_text(
        json.dumps(resumo, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps({k:resumo[k] for k in (
        "base_n","treino_n","teste_n","beta_lucro","beta_intervalo_confianca_95",
        "principal","baseline_ano","heterocedasticidade_breusch_pagan_pvalor",
        "sensibilidade_beta_todos_anos","sensibilidade_beta_ano12"
    )}, ensure_ascii=False, indent=2))
    return resumo


def main() -> None:
    ap = argparse.ArgumentParser(description="Entrega 2 - regressão DashBird")
    ap.add_argument("--dados", type=Path, required=True, help="CSV indicadores_cti.csv")
    ap.add_argument("--saida", type=Path, default=Path("resultados_regressao"))
    args = ap.parse_args()
    processar(args.dados, args.saida)


if __name__ == "__main__":
    main()
