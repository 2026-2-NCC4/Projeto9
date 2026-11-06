# DashBird — Projeto Interdisciplinar: Ciência de Dados | Entrega 2

**FECAP — 2º semestre de 2026**  
**Projeto:** DashBird | Inteligência Financeira  
**Parceiro:** CTI  
**Integrantes:** Breno Frederico Gonzalez Groba, Artur Loreto, Gustavo Archangelo e Luiz Antonio Santos Silva.

## Aplicação publicada

**Acesso ao dashboard:** https://projeto9-qniy57reztrsml8iankmqj.streamlit.app/

**Credenciais de acesso para avaliação:**

- **Usuário:** `admin`
- **Senha:** `1234`

> Credenciais fornecidas pelo grupo para acesso de avaliação. Verifique o login e as funcionalidades em janela anônima antes da submissão. Utilize essas credenciais apenas para a versão demonstrativa, com dados simulados.

**Repositório institucional:** https://github.com/2026-2-NCC4/Projeto9  
**Repositório da publicação (fork):** https://github.com/Archangeloo/Projeto9

O deploy atual utiliza uma cópia do repositório em conta pessoal. Para a avaliação pelo repositório oficial da FECAP, confirmar que os arquivos necessários e este link também constam em `2026-2-NCC4/Projeto9`.

## Arquivos desta pasta

- `Relatorio_Entrega2_DashBird_Ciencia_de_Dados.pdf`: relatório técnico da disciplina, com metodologia, integração da Entrega 1, componentes do software, indicadores, visualizações, validações, limitações e link da aplicação.
- `README.md`: resumo da entrega, instruções de execução e acesso.

Os arquivos Python e as bases não são duplicados aqui; ficam na pasta `src/Entrega 2`, separada em **Frontend** e **Backend**.

## Estrutura do código

```text
src/
└── Entrega 2/
    ├── Frontend/
    │   ├── app.py
    │   ├── ui_contabilidade.py
    │   └── .streamlit/config.toml
    └── Backend/
        ├── core/              # módulos de cálculo e de indicadores
        ├── dados/             # CSV original e bases preparadas
        ├── scripts/           # preparação, importação, validação e regressão
        ├── relatorios/        # dicionários e relatório de validação
        └── testes/
```

## O que foi implementado

- Preparação e integração de dados simulados do Balanço Patrimonial, DRE e Fluxo de Caixa, originados de `Demonstrativo Fecap v3.csv`.
- Base para o painel com **14.400 registros**, correspondentes a **1.200 cenários** ao longo de **12 anos simulados**.
- Visões de receita, resultado operacional, EBITDA, lucro, margens, geração e saldo de caixa.
- Integração das **25 definições contábeis** da planilha de Contabilidade e Finanças: liquidez (6), endividamento (9), resultado (6) e valor econômico (4).
- Filtros por cenário e período, comparações, gráficos e simulação didática de alterações em receitas e custos.
- Script de validação; a documentação atual registra **15 verificações aprovadas** sobre base, fórmulas e reconciliações.

## Como executar localmente

A partir da raiz do repositório, com Python instalado:

```bash
python -m pip install -r requirements.txt
python -m streamlit run "src/Entrega 2/Frontend/app.py"
```

Manter o `requirements.txt` de instalação do dashboard na raiz do repositório de publicação. **Não** versionar `.streamlit/secrets.toml` nem credenciais.

Para habilitar o acesso demonstrativo no Streamlit Community Cloud, em **Manage app → Settings → Secrets** (somente se os dados puderem ser acessados publicamente):

```toml
[auth]
allow_demo = true
```

## Validação de dados

```bash
python "src/Entrega 2/Backend/scripts/validar_dados.py"
python -m unittest discover -s "src/Entrega 2/Backend/testes" -p "test_*.py"
```

Os cenários são fictícios; médias entre cenários não representam soma de operações nem probabilidades. Parte dos indicadores de liquidez não é calculável no Ano 12 devido a ausências na planilha de referência. O simulador é exploratório e não atualiza automaticamente todos os demonstrativos.

## Conferência antes de entregar

- [ ] Enviar este PDF e README ao repositório oficial, em `documentos/Entrega 2/Projeto Interdisciplinar Ciencia de Dados/`.
- [ ] Verificar que `src/Entrega 2/Frontend` e `src/Entrega 2/Backend` estão no repositório oficial.
- [ ] Confirmar link e testar as credenciais de avaliação (`admin` / `1234`) em janela anônima.
- [ ] Testar filtros, gráficos, indicadores contábeis, liquidez nos Anos 11 e 12 e simulações.
- [ ] Anexar uma captura de tela da área interna, caso a equipe queira reforçar as evidências.
- [ ] Atualizar o README principal do GitHub com o link do dashboard.

**Requisito acadêmico de referência:** dashboard funcional e publicado na nuvem, script Python, ao menos cinco indicadores, filtros e comparações, integração à Entrega 1 e documentação de execução, fontes, fórmulas e limitações.
