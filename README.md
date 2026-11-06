
# FECAP — Fundação Escola de Comércio Álvares Penteado

<p align="center">
  <a href="https://www.fecap.br/">
    <img src="[https://www.fecap.br/wp-content/uploads/2023/12/logo-fecap.png](https://camo.githubusercontent.com/9640a318074cf476f8f30d06059763c45be295736ae6e618e824b21b031e74dc/68747470733a2f2f656e637279707465642d74626e302e677374617469632e636f6d2f696d616765733f713d74626e3a414e6439476352685a5072526138394b6d61305a5a6f67786d3070692d74436e5f544c4b65484756787977702d4c584146475233423144506f75414a5948674b5a4756305854456634414526757371703d434155)" alt="FECAP" width="200">
  </a>
</p>

# DashBird — Inteligência Financeira

**Grupo:** Los Meninos do Back  
**Instituição:** FECAP  
**Projeto Interdisciplinar — 2026/2**

## Integrantes

- [Breno Frederico Gonzalez Groba](https://www.linkedin.com/in/breno-groba/)
- [Artur Loreto](https://www.linkedin.com/in/artur-loreto/)
- [Gustavo Archangelo](https://www.linkedin.com/in/gustavo-archangelo/)
- [Luiz Antonio Santos Silva](https://www.linkedin.com/in/luiizsilva/)

## Professores orientadores

- Eduardo Savino Gomes
- Rodnil Lisbôa
- Luis Fernando dos Santos Pires
- Mauricio Lopes Da Cunha

<p align="center">
  <img src="imagens/dashbird.jpg" alt="DashBird" width="780">
</p>

---

## 🌐 Acesse o DashBird

**Dashboard publicado no Streamlit Cloud:**

https://projeto9-qniy57reztrsml8iankmqj.streamlit.app/

**Credenciais de demonstração:**

- **Usuário:** `admin`
- **Senha:** `1234`

O acesso é destinado à avaliação acadêmica do projeto, utilizando dados financeiros simulados.

---

## Sobre o projeto

O **DashBird** é uma plataforma de inteligência financeira desenvolvida por estudantes de Ciência da Computação da FECAP, como parte do Projeto Interdisciplinar em parceria com a CTI.

O projeto tem como objetivo apoiar a análise e interpretação de dados financeiros por meio de indicadores, gráficos interativos, comparações entre cenários e simulações.

A plataforma transforma dados financeiros em informações organizadas, facilitando o acompanhamento de resultados e o apoio à tomada de decisões.

## Funcionalidades

### Visão geral

Apresenta os principais indicadores financeiros:

- Receita
- Resultado operacional
- Lucro líquido
- EBITDA
- Geração líquida de caixa
- Saldo final de caixa
- Ativo total
- Margem operacional

### Contabilidade e Finanças

Disponibiliza indicadores de liquidez, endividamento, rentabilidade e valor econômico.

### Fluxo de caixa

Permite analisar a geração de caixa, os saldos financeiros e sua evolução ao longo dos períodos simulados.

### Comparação de cenários

Possibilita comparar diferentes cenários financeiros e analisar seus resultados.

### Simulador financeiro

Permite realizar análises de sensibilidade por meio da alteração de premissas financeiras.

### Análises estatísticas

Apresenta recursos de análise exploratória, gráficos e indicadores estatísticos.

### Filtros interativos

O usuário pode selecionar:

- Ano simulado
- Cenário individual
- Média simples dos cenários
- Intervalo de anos

---

## Base de dados

A plataforma utiliza dados financeiros simulados disponibilizados no contexto do projeto com a CTI.

A base preparada contempla:

- **1.200 cenários financeiros**
- **12 anos simulados**
- **14.400 combinações de ano e cenário**

Os dados foram preparados e organizados utilizando Python, permitindo sua utilização nos indicadores e gráficos do dashboard.

---

## Tecnologias utilizadas

| Tecnologia | Finalidade |
|---|---|
| Python | Desenvolvimento da aplicação e processamento dos dados |
| Streamlit | Interface web do dashboard |
| Pandas | Manipulação e análise dos dados |
| NumPy | Operações numéricas |
| Plotly | Visualização de dados e gráficos interativos |
| GitHub | Versionamento e organização do projeto |
| Streamlit Cloud | Publicação da aplicação na nuvem |

## Arquitetura do sistema

O DashBird está organizado em Frontend e Backend.

**Frontend**

Responsável pela interface, navegação, apresentação dos indicadores, gráficos e interação com o usuário.

**Backend**

Responsável pelo processamento dos dados, cálculos financeiros, indicadores contábeis, scripts de preparação e validação.

A aplicação utiliza o Streamlit como serviço principal, integrando os componentes do Frontend aos módulos Python do Backend.

---

## Estrutura de pastas

```text
Projeto9/
│
├── README.md
│
├── documentos/
│   ├── README.md
│   ├── Entrega 1/
│   │   ├── Análise Inferencial de Dados/
│   │   ├── Contabilidade e Finanças/
│   │   ├── Engenharia de Software e Arquitetura de Sistemas/
│   │   └── Projeto Interdisciplinar Ciencia de Dados/
│   │
│   └── Entrega 2/
│       ├── Análise Inferencial de Dados/
│       ├── Contabilidade e Finanças/
│       ├── Engenharia de Software e Arquitetura de Sistemas/
│       └── Projeto Interdisciplinar Ciencia de Dados/
│
├── imagens/
│   └── dashbird.jpg
│
└── src/
    ├── Entrega 1/
    │   ├── Frontend/
    │   └── Backend/
    │
    └── Entrega 2/
        ├── Frontend/
        │   ├── app.py
        │   ├── ui_contabilidade.py
        │   ├── requirements.txt
        │   └── .streamlit/
        │
        ├── Backend/
        │   ├── core/
        │   ├── dados/
        │   ├── scripts/
        │   ├── testes/
        │   ├── relatorios/
        │   └── referencias/
        │
        └── README_Deploy_DashBird.md
```

---

## Como executar o projeto

### Pré-requisitos

- Python instalado
- pip
- Git (para clonar o repositório)

### 1. Clonar o repositório

```bash
git clone https://github.com/2026-2-NCC4/Projeto9.git
```

### 2. Acessar a pasta do projeto

```bash
cd Projeto9
```

### 3. Instalar as dependências

```bash
python -m pip install -r "src/Entrega 2/Frontend/requirements.txt"
```

### 4. Executar a aplicação

```bash
python -m streamlit run "src/Entrega 2/Frontend/app.py"
```

A aplicação será disponibilizada no navegador, normalmente em:

http://localhost:8501

Para utilizar o login localmente, é necessário configurar as credenciais por variáveis de ambiente ou pelos Secrets do Streamlit.

Mais informações estão disponíveis no arquivo:

[src/Entrega 2/README_Deploy_DashBird.md](src/Entrega%202/README_Deploy_DashBird.md)

---

## Entregas acadêmicas

Toda a documentação está organizada por disciplina e etapa.

### Entrega 1

[Consultar documentos da Entrega 1](documentos/Entrega%201/)

### Entrega 2

[Consultar documentos da Entrega 2](documentos/Entrega%202/)

**Relatório de Ciência de Dados — Entrega 2:**

[Visualizar relatório do DashBird](documentos/Entrega%202/Projeto%20Interdisciplinar%20Ciencia%20de%20Dados/DashBird_Entrega2_Relatorio.pdf)

**Documentação completa:**

[Índice das entregas acadêmicas](documentos/README.md)

---

## Código-fonte

- [Frontend — Entrega 2](src/Entrega%202/Frontend/)
- [Backend — Entrega 2](src/Entrega%202/Backend/)

---

## Referências

- [FECAP](https://www.fecap.br/)
- [CTI](https://www.cti.com.br/)
- [Python](https://www.python.org/)
- [Streamlit](https://streamlit.io/)
- [Pandas](https://pandas.pydata.org/)
- [Plotly](https://plotly.com/python/)

## Licença

Este projeto está associado à licença Creative Commons Attribution 4.0 International (CC BY 4.0).

[Consultar a licença](https://creativecommons.org/licenses/by/4.0/)
