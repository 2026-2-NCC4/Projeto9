# CTI — Dicionário de indicadores (base analítica v2)

**Contexto:** concessão de setor não informado; 1.200 cenários alternativos × 12 anos simulados. **Moeda de exibição:** R$ por convenção do trabalho. **Fonte única:** `Demonstrativo Fecap v3.csv` (CTI). **Granularidade:** ano simulado e cenário. As definições abaixo refletem as contas encontradas na fonte; não substituem sua validação pela CTI.

| Indicador / unidade | Fonte ou cálculo exato | Interpretação, uso e validação |
|---|---|---|
| Receita (R$) | `DRE - Receita` | Receita contábil da DRE, preservada do arquivo original |
| Tributos DRE (R$ com sinal) | `DRE - Tributos` | Componente do resultado operacional, sinal preservado |
| Custos DRE (R$ com sinal) | `DRE - Custos` | Despesa/custo informado com sinal; não tomar valor absoluto para cálculo operacional |
| Resultado operacional (R$) | `DRE - Resultado Operacional` | Valor original. Reconciliado com receita + tributos + custos + depreciação/amortização (tolerância R$ 0,01) |
| EBITDA (R$) | `DRE - EBITDA` | Conta informada na fonte; não assumida equivalência com EBIT + D&A sem as regras da CTI |
| Lucro líquido (R$) | `DRE - Resultado Líquido` | Resultado contábil da DRE, não é saldo de caixa |
| Margem operacional (%) | `DRE - Resultado Operacional ÷ DRE - Receita × 100` | N/D quando receita = 0 |
| Margem líquida (%) | `DRE - Resultado Líquido ÷ DRE - Receita × 100` | N/D quando receita = 0 |
| Margem EBITDA (%) | `DRE - EBITDA ÷ DRE - Receita × 100` | N/D quando receita = 0 |
| Saldo inicial de caixa (R$) | `FLU - Saldo Inicial` | Disponibilidade inicial no demonstrativo FLU |
| Recebimentos (R$) | `FLU - Receita` | Não igualar mecanicamente à receita da DRE |
| Tributos FLU (R$) | `FLU - Tributos` | Componente do caixa, valor/sinal original |
| Custos FLU (R$) | `FLU - Custos` | Saída de caixa registrada no FLU |
| Investimentos FLU (R$) | `FLU - Investimentos` | Componente de desembolsos/fluxos de investimento |
| Resultado financeiro FLU (R$) | `FLU - Resultado Financeiro` | Valor líquido: `FLU - Entradas + FLU - Despesas Financeiras`, sem dupla contagem |
| IR e CSLL FLU (R$) | `FLU - Imposto de Renda e Contribuição Social` | Parcela de caixa de IR/CSLL registrada |
| Distribuição aos acionistas (R$) | `FLU - Distribuição para Acionista` | Saída/entrada conforme sinal da fonte |
| Geração líquida de caixa (R$) | `FLU - Geração de Caixa` | Confere com a soma das sete parcelas FLU (tolerância R$ 0,01) |
| Saldo final de caixa (R$) | `FLU - Saldo Final` | Confere com saldo inicial + geração de caixa (tolerância R$ 0,01) |
| Ativo total (R$) | `BAL - Total do Ativo` | Fonte preservada; valores negativos exigem esclarecimento da CTI |
| Passivo total (R$ com sinal) | `BAL - Total do Passivo` | Sinal negativo preservado no arquivo recebido; ativo + passivo ~ R$ 0,025 devido à diferença da fonte |

## Médias entre cenários

- Para contas monetárias: média aritmética entre cenários selecionados no mesmo ano, **não** soma.
- Para margens: `100 × média(resultado) / média(receita)`. Não utilizar `média(margens)` para substituir a razão dos valores médios.
- Probabilidades e pesos dos cenários **não foram confirmados**, portanto não há valor esperado estatístico demonstrado.

## Regras do diagnóstico (heurísticas de atenção)

1. Lucro líquido positivo + geração líquida de caixa negativa → aviso de diferença entre lucro e caixa.
2. Geração negativa + distribuição aos acionistas negativa → sinalizar coexistência de saída de distribuição.
3. Saldo final de caixa negativo → ponto de atenção a verificar, não diagnóstico de insolvência.
4. Ativo total negativo → necessidade de esclarecer sinal/estrutura da simulação.
5. Margem operacional abaixo da meta escolhida no dashboard → comparativo **hipotético**, nunca meta oficial da CTI.

## Verificação

Rodar `python scripts/validar_dados.py` para comparar **todas as combinações**, incluindo 21 contas contra os números originais. Resultados e limitações em `relatorios/validacao_dados.md`.
