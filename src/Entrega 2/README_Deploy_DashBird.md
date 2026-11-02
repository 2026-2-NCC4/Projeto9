# DashBird | Entrega 2 — Frontend e Backend

Estrutura preparada para integrar ao repositório `2026-2-NCC4/Projeto9`.
**Este pacote não altera automaticamente o GitHub.**

## Organização

- `Frontend/app.py`: ponto de entrada do dashboard Streamlit.
- `Frontend/ui_contabilidade.py`: componentes das telas de Contabilidade e Finanças.
- `Frontend/requirements.txt`: dependências para deploy.
- `Frontend/.streamlit/config.toml`: configuração de tema.
- `Backend/core/`: regras de cálculo e processamento financeiro.
- `Backend/dados/`: base original, dados processados e indicadores extraídos da planilha.
- `Backend/scripts/`: preparação, importação, validação e regressão.
- `Backend/testes/`: testes automatizados.
- `Backend/relatorios/`: dicionários e relatórios de validação.
- `Backend/referencias/`: planilha original da Entrega 1 usada pela extração.

O aplicativo é **um único Streamlit**, não requer API nem servidor Backend
separado. O Frontend adiciona a pasta Backend ao caminho de importações do
Python antes de carregar os módulos `core`.

## Aplicação na cópia local do repositório

Mescle a pasta `src` deste pacote com a pasta `src` existente.
Preserve as pastas `documentos/Entrega 1` e `documentos/Entrega 2` do
repositório; este pacote altera **somente** o conteúdo de `src/Entrega 2`.

## Executar pelo terminal na raiz do repositório

Instalação:

```powershell
py -m pip install -r "src/Entrega 2/Frontend/requirements.txt"
```

Opcionalmente, habilite o modo de demonstração em execução local:

```powershell
Copy-Item "src/Entrega 2/Frontend/.streamlit/secrets.toml.example" "src/Entrega 2/Frontend/.streamlit/secrets.toml"
```

Executar:

```powershell
py -m streamlit run "src/Entrega 2/Frontend/app.py"
```

Em ambiente público, configure no painel de Secrets do Streamlit
`[auth] allow_demo = true` somente se o acesso demonstrativo for desejado.
**Não inclua `secrets.toml` no GitHub.**

## Configurar o Streamlit Community Cloud

- Repository: `2026-2-NCC4/Projeto9`
- Branch: `main`
- Main file path: `src/Entrega 2/Frontend/app.py`
- Dependências: `src/Entrega 2/Frontend/requirements.txt`
- Configuração visual: `src/Entrega 2/Frontend/.streamlit/config.toml`

No GitHub, confira a grafia exata do nome `Entrega 2`, incluindo o espaço.
O Streamlit busca `requirements.txt` junto ao app e pode reconhecer a
configuração colocada na mesma pasta do arquivo de entrada.

## Testes a partir da raiz do repositório

```powershell
py -m unittest discover -s "src/Entrega 2/Backend/testes" -p "test_*.py"
py "src/Entrega 2/Backend/scripts/validar_dados.py"
```

Regressão inferencial (dependências opcionais, não necessárias para
publicar o dashboard):

```powershell
py -m pip install -r "src/Entrega 2/Backend/requirements_analise_regressao.txt"
py "src/Entrega 2/Backend/scripts/analise_regressao.py" --dados "src/Entrega 2/Backend/dados/indicadores_cti.csv" --saida "resultados_regressao"
```

O relatório PDF e o notebook de regressão devem ficar em
`documentos/Entrega 2/Análise Inferencial de Dados` e não precisam ser
carregados pelo Streamlit.

## Observações

- Os arquivos `Demonstrativo Fecap v3.csv` e a planilha de Contabilidade
  são grandes; estão incluídos para reprodutibilidade. O dashboard em
  produção usa os arquivos já processados em `Backend/dados/`.
- Os dados são simulados; não representam resultados reais da CTI.
- Os indicadores de liquidez podem ser indisponíveis no Ano 12, como já
  explicado na aplicação.
