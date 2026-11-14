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

Opcionalmente, copie o exemplo de configuração. A recuperação por chave
funciona mesmo sem este arquivo:

```powershell
Copy-Item "src/Entrega 2/Frontend/.streamlit/secrets.toml.example" "src/Entrega 2/Frontend/.streamlit/secrets.toml"
```

Executar:

```powershell
Set-Location "src/Entrega 2/Frontend"
py -m streamlit run app.py
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

## Recuperação de senha

### Uso sem SMTP (padrão)

A recuperação funciona **sem provedor de e-mail e sem configurar SMTP**.
Ao criar uma conta, o aplicativo apresenta uma chave de recuperação. Copie-a
ou use **Baixar chave de recuperação**, guarde o arquivo em local seguro e
marque **Guardei minha chave em um local seguro** para continuar.

Quem já possui conta deve entrar na plataforma, abrir **Segurança da conta**
na barra lateral, informar a senha atual e clicar em **Gerar nova chave de
recuperação**. A chave aparece para ser salva e substitui qualquer chave anterior.
Ela não pode ser consultada novamente após fechar essa tela; é possível gerar
outra confirmando a senha atual.

Se esquecer a senha, na aba **Entrar**, abra **Esqueci minha senha**, informe o
e-mail da conta, cole a chave guardada, informe e confirme a nova senha e clique
em **Redefinir senha**. Salve a nova chave apresentada, clique em **Voltar para
entrar** e faça login com a nova senha.

A chave é aleatória, tem 256 bits, fica vinculada à conta e não tem prazo de
15 minutos: vale até ser usada ou substituída. Cada recuperação troca a senha,
invalida a chave e eventuais códigos de e-mail anteriores e emite uma nova chave.
Somente o hash da chave fica no banco; o login não retorna a chave. Senhas
continuam protegidas com PBKDF2. Cadastro e chave, assim como troca de senha e
renovação da chave, são persistidos na mesma transação.

As tabelas são criadas automaticamente em SQLite ou PostgreSQL e preservam as
contas existentes. Contas antigas que já perderam a senha e ainda não possuem
chave precisam de ajuda do responsável pela plataforma, com confirmação de
identidade. Informar apenas um e-mail não autoriza trocar a senha.
Credenciais fixas de `[auth]` ou `CTI_USER`/`CTI_PASSWORD` continuam sendo alteradas
pela configuração.

### Envio por e-mail (opcional)

Caso seja configurado um servidor SMTP no futuro, a mesma tela também permite
solicitar um código por e-mail. Sem essa configuração, a opção de envio não é
exibida e a recuperação por chave continua disponível. Para habilitar o envio,
use o painel de Secrets do Streamlit Cloud ou o arquivo `secrets.toml`:

```toml
[smtp]
host = "smtp.seu-provedor.com"
port = 587
username = "seu-usuario-smtp"
password = "sua-senha-de-aplicativo"
from_email = "acesso@seu-dominio.com"
use_ssl = false
```

Para carregar `Frontend/.streamlit/secrets.toml` localmente, execute o Streamlit
a partir da pasta `src/Entrega 2/Frontend` com `py -m streamlit run app.py`.
Outra opção é configurar as variáveis de ambiente `CTI_SMTP_HOST`,
`CTI_SMTP_PORT`, `CTI_SMTP_USER`, `CTI_SMTP_PASSWORD`, `CTI_SMTP_FROM` e
`CTI_SMTP_SSL`; elas têm precedência sobre a seção `[smtp]`.
O envio exige TLS: use `use_ssl = false` para STARTTLS (porta 587) ou
`use_ssl = true` para TLS implícito (porta 465). Não há novas dependências.

O código de e-mail expira em 15 minutos, é de uso único e tem intervalo mínimo
de 60 segundos entre envios para a mesma conta, persistido no banco.
Um novo envio invalida o código anterior. A resposta de solicitação é a mesma
para contas existentes e desconhecidas; falhas de envio são registradas no log
sem expor o e-mail ou o código. Se uma entrega falhar, aguarde 60 segundos antes
de tentar novamente. Recuperar por e-mail também emite uma nova chave para guardar.

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
