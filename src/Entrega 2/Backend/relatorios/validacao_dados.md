# CTI — Relatório de Validação da Base Financeira

## Escopo
- Fonte: `Demonstrativo Fecap v3.csv` (preservada); base tratada: `indicadores_cti.csv`.
- 14,400 registros de pares ano/cenário.
- 1200 cenários; 12 anos simulados.
- 27 contas financeiras comparadas com a fonte linha a linha.
- Valores monetários exibidos como R$ por convenção de apresentação.

## Testes automatizados
- **APROVADO** — Registros de cenários/anos (14.400)
- **APROVADO** — 1.200 cenários
- **APROVADO** — 12 anos
- **APROVADO** — Sem pares duplicados
- **APROVADO** — Sem contas obrigatórias vazias
- **APROVADO** — 100% das contas preservadas frente ao original
- **APROVADO** — Comparação integral com CSV original (erro < R$ 0,01)
- **APROVADO** — Fórmula de margem operacional
- **APROVADO** — Fórmula de margem líquida
- **APROVADO** — Fórmula de margem ebitda
- **APROVADO** — Reconciliação FLU componentes vs geração (R$ 0,01)
- **APROVADO** — Reconciliação FLU saldo inicial + geração = final (R$ 0,01)
- **APROVADO** — Resultado financeiro = entradas + despesas financeiras (R$ 0,01)
- **APROVADO** — DRE resultado operacional = receita + tributos + custos + D&A (R$ 0,01)
- **APROVADO** — BAL ativo + passivo (tolerância R$ 0,10)

## Diferenças máximas observadas (valores absolutos na unidade original)
- Processo versus fonte: 0.00000191
- Ponte do fluxo versus geração: 0.00010633
- Saldo inicial + geração versus saldo final: 0.00001907
- Financeiro: 0.00001049
- DRE: 0.00008011
- Balanço, ativo + passivo: 0.02520180

## Pontos de atenção para os analistas da CTI
- O conjunto possui 714 registros com ativo total negativo. A origem foi preservada; a interpretação precisa de confirmação.
- No Ano 12, 1170 de 1.200 cenários têm geração líquida de caixa negativa (não é probabilidade de risco).
- A fonte não confirma setor, moeda, metas financeiras nem probabilidade dos cenários.
- Contas do balanço apresentam sinal contábil na fonte; não se ajustaram os sinais.
- EBITDA foi extraído do demonstrativo; não foi substituído por fórmula própria.
- A tolerância para o balanço difere da do fluxo porque a fonte já possui diferença residual de cerca de R$ 0,025.

## Conclusão
**As verificações matemáticas atestam a fidelidade ao arquivo recebido, não a adequação das premissas contábeis do modelo de concessão.**
