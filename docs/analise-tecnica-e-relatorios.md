# Painel TOTALE — Análise Técnica, Melhorias e Sugestões de Relatórios

**Data:** 13/10/2026 · **Commit analisado:** `0233de1` · **Escopo:** `streamlit_app.py`, `pages/`, `components/`, `config/`, `robo/`, `services/`, `tests/`, `.github/`, docs de raiz.

---

## 1. Sumário executivo

O repositório está **em bom estado geral** para um projeto corporativo de porte: lint limpo, 66 testes passando, CI verde, design system próprio, guardas estáticas contra regressão de higiene e documentação acima da média. Os problemas não são de "falta de capricho" — são de **concentração de risco**: dado sensível exposto sem autenticação, escrita destrutiva no backend, componentes duplicados e páginas monolíticas que travam a evolução.

| Prioridade | Achado | Impacto | Esforço |
|---|---|---|---|
| 🔴 P0-1 | **16 das 17 páginas não exigem login** — dados operacionais reais acessíveis a qualquer visitante da URL | Vazamento de dados pessoais (LGPD) + exposição competitiva | 1–2 dias |
| 🔴 P0-2 | **IDs reais de Google Sheets/Drive hardcoded** em repositório **público** (`config/settings.py:25-28`) | Superfície de ataque + possível exposição de dados | 2 h |
| 🔴 P0-3 | **`LICENSE` é Apache-2.0, mas o README anuncia "Proprietary"** | Concede direitos de uso/modificação que a empresa talvez não queira | 30 min (decisão) |
| 🔴 P0-4 | **`pages/login.py` com cadastro aberto** (`Criar Nova Conta`) + SQLite local + hash legado divergente | Porta dos fundos se for registrada na navegação | 1 h |
| 🟠 P1-1 | **Escrita reescreve a planilha inteira** (`pages/gestao_ativos.py:208-247`) com leitura cacheada 300 s | Perda de dados em escrita concorrente | 2–3 dias |
| 🟠 P1-2 | **Design System duplicado dentro das páginas** (7 componentes reimplementados) | Correções aplicadas em 1 lugar não chegam às outras páginas | 2–3 dias |
| 🟠 P1-3 | **`main()` de 1.019 linhas** em `rota_inicial.py` (+ outras 9 funções > 150 linhas) | Impossível testar, revisar ou refatorar com segurança | gradual |
| 🟠 P1-4 | **Regras de negócio sem teste** — `indicadores.py`, `dashboard_meta`, rotas e volumetria não têm cobertura | Regressão silenciosa em fechamento de mês | 1 semana |
| 🟡 P2-1 | **11 dependências não usadas** (duckdb, matplotlib, pydeck, pytz, gspread-dataframe…) | Build lento no Streamlit Cloud, superfície de CVE | 2 h |
| 🟡 P2-2 | **Camada de dados inexistente** — cada página baixa/parseia/cacheia do seu jeito | TTLs inconsistentes, chamadas duplicadas ao Sheets | 1 semana |
| 🟡 P2-3 | **Sem `pyproject.toml`, `config.toml`, pre-commit ou lockfile** | Reproducibilidade e padronização dependem de memória | 1 dia |
| 🟡 P2-4 | **README com imagens quebradas** (`docs/screenshots/*.png` inexistentes) | Perda de credibilidade na primeira impressão do repo | 1 h |

### Como estas conclusões foram verificadas

```bash
ruff check .                                  # All checks passed!
pytest -q                                     # 66 passed
python tests/test_sintaxe.py                  # guardas estáticas
```

Métricas levantadas: **24.030 linhas** em `pages/` (19 arquivos), 5.251 em `components/`, 1.669 em `tests/`, 17 rotas registradas em `st.navigation`, **16 funções com mais de 150 linhas**, **47 nomes de função/classe duplicados entre arquivos**.

---

## 2. O que já está bom (não desperdiçar)

1. **Design System de verdade** — `components/componentes.py` + `dashboard_kit.py` com fábricas de gráficos, filtros persistentes, exportação formatada e insights automáticos. Isso é raro em projeto interno e é o maior ativo do repo.
2. **Guardas estáticas de higiene** (`tests/test_higiene_repositorio.py`) — asset órfão, diretório vazio, caminho de máquina e árvore do README são verificados por teste. Excelente prática.
3. **Motor de datas isolado e documentado** (`pages/datas_dashboard.py`) — ISO × BR sem inversão, sem depender de Streamlit. É exatamente o padrão a repetir para outras regras.
4. **Robô de ingestão separado da UI** — `robo/robo_engine.py` não importa Streamlit (só a camada de apresentação `robo_local.py` importa), tem `ArquivoBloqueadoError` e verificação de estabilidade de arquivo. É exatamente a separação domínio × interface que falta em `pages/`.
5. **Resiliência de rede considerada** — retries, tratamento da página HTML de confirmação do Drive (`confirm=t`), inferência de separador/encoding de CSV, fontes independentes com degradação parcial.
6. **Saúde de dados e alertas já modelados** (`components/saude_dados.py`, `components/alertas_automaticos.py`) — frescor de 15/60 min com estados ok/alerta/crítico. Falta apenas virar relatório visível (ver §4.E).
7. **CI enxuto e verde** em push e PR, com `timeout-minutes` e cache de pip.

---

## 3. Melhorias recomendadas (achados com evidência)

### 🔴 P0-1 — Autenticação só existe em 1 página

**Evidência:** o único gate do app está em `pages/gestao_ativos.py:799` (`if not st.session_state.autenticado: st.stop()`). Busca por gate em todos os outros arquivos retorna vazio — `home`, `indicadores`, `dashboard_meta`, `pontos`, `volumetria`, `rota_*`, `quebra_*`, `retorno`, `p_atendimento`, `consultivo`, `alertas`, `envio_excel` e `assinatura` renderizam dados operacionais sem login.

**Impacto:** o README divulga a demo pública (`painel-totale.streamlit.app`). Quem tiver o link vê nome, RE, login e produção de técnicos reais, além de churn por contrato. Para a LGPD, dados de trabalhadores identificáveis em painel aberto é exposição direta.

**Correção sugerida — gate central, uma vez só:**

```python
# components/auth.py  (novo)
from __future__ import annotations

import hmac
import time
from dataclasses import dataclass

import streamlit as st

_TTL_SESSAO_SEGUNDOS = 8 * 3600
_PERFIS = {
    "admin": {"ler", "escrever", "editar", "desligar", "importar", "auditoria"},
    "supervisor": {"ler", "escrever", "editar", "desligar", "importar"},
    "operador": {"ler", "escrever", "editar"},
    "leitura": {"ler"},
}


@dataclass(frozen=True)
class Usuario:
    login: str
    nome: str
    role: str
    bases: tuple[str, ...]

    def pode(self, acao: str) -> bool:
        return acao in _PERFIS.get(self.role, set())


def _contas() -> dict[str, dict]:
    try:
        contas = dict(st.secrets.get("usuarios", {}))
    except Exception:
        return {}
    return {str(k).strip().lower(): dict(v) for k, v in contas.items()}


def _validar(login: str, senha: str) -> Usuario | None:
    dados = _contas().get(login.strip().lower())
    if not dados:
        return None
    esperada = str(dados.get("senha", ""))
    # hmac.compare_digest evita comparação sensível a tempo
    if not esperada or not hmac.compare_digest(senha, esperada):
        return None
    bases = dados.get("bases", [])
    if isinstance(bases, str):
        bases = [bases]
    return Usuario(
        login=login.strip().lower(),
        nome=str(dados.get("nome", login)),
        role=str(dados.get("role", "leitura")).lower(),
        bases=tuple(str(b) for b in bases),
    )


def exigir_login() -> Usuario:
    """Bloqueia a página inteira até haver sessão válida. Chame no entrypoint."""
    sessao = st.session_state.get("_auth")
    if sessao and time.time() - sessao["ts"] < _TTL_SESSAO_SEGUNDOS:
        sessao["ts"] = time.time()  # renova a cada interação
        return sessao["usuario"]

    st.session_state.pop("_auth", None)
    st.title("🔐 Portal TOTALE")
    st.caption("Acesso restrito. Use as credenciais corporativas.")
    with st.form("form_login"):
        login = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")
    if entrar:
        usuario = _validar(login, senha)
        if usuario:
            st.session_state["_auth"] = {"usuario": usuario, "ts": time.time()}
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    st.stop()  # nada abaixo é renderizado sem sessão válida


def usuario_atual() -> Usuario | None:
    sessao = st.session_state.get("_auth")
    return sessao["usuario"] if sessao else None


def botao_sair() -> None:
    if st.sidebar.button("Sair"):
        st.session_state.pop("_auth", None)
        st.rerun()
```

```python
# streamlit_app.py — 3 linhas no main(), antes de pg.run()
from components.auth import botao_sair, exigir_login

usuario = exigir_login()          # bloqueia tudo abaixo
st.session_state["usuario_atual"] = usuario
...
botao_sair()                      # na sidebar corporativa
```

**Ao aplicar, garantir:** (a) copiar `[usuarios.*]` para os secrets do Streamlit Cloud **antes** do deploy, senão o app trava para todos; (b) trocar as senhas em texto por hash PBKDF2 dentro dos secrets (formato `pbkdf2_sha256$...` já usado em `gestao_ativos.py`); (c) migrar `gestao_ativos.py` para consumir o mesmo `Usuario` — fim das duas autenticações paralelas.

---

### 🔴 P0-2 — IDs de infraestrutura versionados em repositório público

**Evidência:** `config/settings.py:25-28` traz IDs reais como fallback:

```python
_DEFAULT_SHEET_ID_ATIVOS = "1LQKDcLshC6XSXLBVWaEYSpxrro6uydyU9pwDLc38pEg"
_DEFAULT_SHEET_ID_PROD = "11Dp9WdZYUrT_LBvfo07Mi8muKXZykU7v"
_DEFAULT_DRIVE_ID_CONS = "1YOWJ0HuGcEP2vJaZwl2kcgrtNgsoMBDs"
_DEFAULT_DRIVE_ID_INDICADORES = "1k6NrvdZzdSV_sGOQkMKIssEhh7p7wyO0"
```

**Impacto:** o repositório é público (`gh repo view` → `isPrivate: false`). Qualquer pessoa passa a conhecer os identificadores internos das bases, pode testar exportações (`export?format=csv`) e monitorar mudanças de estrutura. Se alguma dessas planilhas estiver compartilhada como "qualquer pessoa com o link" (comum durante desenvolvimento), os dados são legíveis sem login.

**Correção:**

1. Mover os 4 IDs para `.streamlit/secrets.toml` e para os secrets do Cloud.
2. Trocar o fallback por **falha explícita e amigável** — nunca por ID real:

```python
def _obrigatorio(chave: str) -> str:
    valor = obter_secret(chave)
    if not valor:
        raise RuntimeError(
            f"Configuração '{chave}' ausente. Defina em .streamlit/secrets.toml "
            "ou nas variáveis de ambiente do deploy."
        )
    return valor
```

3. Verificar (e revogar) o compartilhamento por link das planilhas e rotacionar a service account se houver dúvida.
4. Sanear o histórico do Git se o repositório precisa continuar público (`git filter-repo`) — o histórico mantém os IDs mesmo após remover do arquivo.

---

### 🔴 P0-3 — Licença contraditória

**Evidência:** `LICENSE` = **Apache License 2.0**. `README.md:13` exibe o selo `License-Proprietary-red`. Um repositório Apache-2.0 concede a qualquer pessoa uso comercial, modificação e redistribuição (com os devidos créditos e sem garantia) — o oposto de "proprietário".

**Ação:** escolher o caminho correto e alinhar os três pontos (LICENSE, selo do README, política de contribuição):

- **Software proprietário:** trocar o arquivo `LICENSE` por um aviso de copyright "Todos os direitos reservados", fechar o repositório (ou usar licença de avaliação) e revisar a seção "Contribuindo", que hoje convida a forks.
- **Código aberto de fato:** manter Apache-2.0 e trocar o selo para `License-Apache_2.0-blue`, registrando no README o que NÃO está aberto (dados, nomes de clientes, credenciais).

Como este painel normalmente carrega dados de clientes, a recomendação é a primeira opção — aliás, é o mesmo motivo pelo qual o P0-1 é crítico.

---

### 🔴 P0-4 — `pages/login.py`: porta dos fundos e duplicação de autenticação

**Evidência:** `pages/login.py` mantém um cadastro **aberto ao público** (`area_autenticacao`, linha 109 → aba "Criar Nova Conta" → `cadastrar_novo_usuario`, linha 81) gravando em SQLite local (`sqlite3.connect("usuarios.db")`, linha 18). O arquivo **não está registrado** em `st.navigation` (não é acessível hoje), mas:

- é uma armadilha: basta alguém adicioná-lo ao menu para o sistema virar cadastro livre;
- cria um **segundo sistema de senhas**, incompatível com o de `gestao_ativos.py` — o fallback legado de um usa salt `b"totale-legacy"`, o outro usa `b""`, então nenhum hash antigo valida nos dois.

**Ponto positivo:** o `.gitignore` **já cobre** `usuarios.db`, `usuarios.db-journal/-wal/-shm` e `db.sqlite3` (linhas 74-79), e não há nenhum banco versionado (`git ls-files` limpo). Esse risco está bem tratado.

**Correção:** apagar `pages/login.py` (não registrado em `st.navigation`, portanto código morto) e unificar a autenticação no gate central do P0-1, com senhas em PBKDF2 guardadas nos secrets.

---

### 🟠 P1-1 — Escrita no Sheets pode apagar trabalho de outro usuário

**Evidência:** `Repo.cadastrar`/`gravar` (`pages/gestao_ativos.py:459+`) leem a tabela inteira com `@st.cache_data(ttl=300)` (linha 353), alteram a linha em memória e então **regravam o intervalo `A1:{última_col}{n}` com o DataFrame inteiro** (linhas 231-247), limpando o excedente com `batch_clear`.

**Cenário de falha real:** dois supervisores cadastram técnicos em até 5 minutos. O segundo lê a base **cacheada** (sem o cadastro do primeiro), monta o DataFrame e sobrescreve a aba — o primeiro cadastro desaparece da planilha, mas continua no `log_auditoria`, criando divergência entre log e base.

**Correções, em ordem de custo/benefício:**

1. **Escrita por linha, não por planilha.** Para inclusão: `ws.append_row([...])` (já existe `_append_gspread`, linha 195 — hoje só usado no log). Para edição/desligamento: `ws.update(f"A{linha}:H{linha}", [[...]])` localizando a linha pela chave (`RE`), com `ws.col_values(1)` para descobrir o índice.
2. **Invalidar cache antes e depois de escrever.** `_fetch.clear()` já é chamado; o problema é **ler com cache para escrever**. Regra: leitura para exibição pode cachear; leitura para escrita **nunca**.
3. **Deteção de conflito otimista.** Gravar uma coluna `Ultima_Modificacao` (já existe) e recusar a escrita se a linha lida tiver mudado desde a leitura — mensagem: "Registro alterado por outro usuário, recarregue".
4. **Backup diário automático** da planilha (cópia para arquivo `ativos_backup_YYYYMMDD.csv` em pasta do Drive, via GitHub Actions ou Apps Script). Sem isso, um bug de escrita destrói a fonte da verdade.
5. **Alerta de integridade:** comparação diária entre `log_auditoria` e a base — divergência = alerta no painel de alertas automáticos (a infraestrutura já existe).
6. **Médio prazo:** considerar tirar a escrita do Sheets. Google Sheets é ótimo como entrada, ruim como banco transacional. Um SQLite/Postgres/AppSheet com o Sheets apenas como leitura elimina a classe inteira de risco.

---

### 🟠 P1-2 — Design System reimplementado dentro das páginas

**Evidência:** componentes do `components/componentes.py` reescritos localmente (sombreando o import e recebendo correções que não chegam ao restante do app):

| Componente | Definido no Design System | Reimplementado em |
|---|---|---|
| `render_hero` | `componentes.py:1123` | `quebra_geral.py:1610`, `p_atendimento.py:275` |
| `render_kpi` / `render_kpi_sm` | `componentes.py:1469` / `:1495` | `p_atendimento.py:287`, `quebra_geral.py:1462` |
| `render_insight` | `componentes.py:1508` | `p_atendimento.py:328`, `quebra_geral.py:1449` |
| `render_table_html` | `componentes.py:1625` | `quebra_geral.py:1442` |
| `render_section_header` | `componentes.py:1330` | `quebra_geral.py:1430` |
| `injetar_css` | `componentes.py:577` | `quebra_geral.py:1508`, `rota_geral.py:718`, `rota_inicial.py:264`, `p_atendimento.py:54` |
| `Fontes` (tipografia) | `componentes.py:187` | `quebra_geral.py:198` |

Somam-se: `gerar_excel` em 5 arquivos, `Config`/`Configuracoes`/`Utils` em 3–4 arquivos cada, `normalizar_texto` em 4, `buscar_coluna` em 3, `ler_arquivo`/`carregar_arquivo` em 3. **47 nomes duplicados no total.**

**Impacto:** uma melhoria visual (como o Dashboard Kit v2) exige editar 5-6 arquivos; um bug de formatação de número se multiplica; e as páginas "especiais" ficam visualmente desalinhadas das demais.

**Plano de consolidação (incremental, sem big bang):**

1. Criar `components/legado.py` com as versões locais movidas e um teste que proíbe **novas** definições de `render_*(...)` fora de `components/` (guarda estática, no estilo do repo).
2. Migrar uma página por PR, começando pelas menores (`p_atendimento`, depois `quebra_geral`), substituindo a chamada local pela do Design System e validando com `AppTest`.
3. No fim, apagar `components/legado.py` — mesmo padrão de "teste-guarda impede o retorno do órfão" que o repo já usa em `test_refatoracao_arquitetura.py`.

---

### 🟠 P1-3 — Funções monolíticas

**Evidência (top 10 por extensão, medido por AST):**

| Linhas | Local | Função |
|--------:|-------|--------|
| 1019 | `rota_inicial.py:1244` | `main` |
| 591 | `p_atendimento.py:832` | `main` |
| 470 | `volumetria.py:1382` | `main` |
| 384 | `indicadores.py:1665` | `renderizar_visao_tecnicos` |
| 365 | `indicadores.py:1296` | `renderizar_visao_executiva_geral` |
| 292 | `indicadores.py:2053` | `renderizar_painel_executivo_aba` |
| 261 | `rota_geral.py:718` | `_injetar_css` |
| 247 | `quebra_unificada.py:1867` | `main` |
| 245 | `volumetria.py:917` | `render_dataframe` |
| 199 | `p_atendimento.py:54` | `_injetar_css_local` |

**Padrão de correção (o mesmo que já funcionou em `robo/`):** extrair para um módulo **sem Streamlit**, testável puro.

```
services/
├── dominio/            # regras puras: nada de st.*
│   ├── producao.py     # pontos, agrupamentos, projeções
│   ├── rotas.py        # turnos, sequenciamento, km
│   ├── quebra.py       # segmentos ND/Migração/PME/GPON
│   └── sla.py          # aging, prazos, primeira tentativa
└── dados/              # repositórios com cache padronizado
```

Regra prática: se o trecho não chama `st.`, ele não pertence a `pages/`. Um `main()` de página deve ficar na faixa de 40–80 linhas: filtros → chamar serviço → renderizar. Isso destrava o P1-4 automaticamente.

---

### 🟠 P1-4 — Cobertura de testes concentrada nas guardas, não no negócio

**Evidência:** 66 testes, dos quais a maioria é guarda estática (sintaxe, higiene, deprecados, CSS, arquitetura). Há teste real para `home`, `quebra_geral` (`DataLoader`/`Utils`), `dashboard_kit`, `metricas_executivas` e `saude_dados`. **Nada cobre** `indicadores.py` (2.491 linhas), `dashboard_meta.py` (2.202), `rota_inicial.py` (2.267), `volumetria.py` (1.856), `pontos.py`, `retorno.py`, `envio_excel.py`.

**Impacto:** é justamente nessas páginas que moram as regras que fecham o mês (metas, projeção, agrupamento, quebra por segmento). Uma mudança de critério passa no CI e só aparece na reunião de resultados.

**Como atacar (sem parar a operação):**

1. Extrair as funções puras de cada página para `services/dominio/*.py` (passo do P1-3) — a extração é a oportunidade natural de escrever o teste.
2. Priorizar por risco: **1)** fechamento de metas e projeção (`dashboard_meta`); **2)** classificação de quebra e segmentos (`criterios.py` — já parcialmente coberto, ampliar com casos reais); **3)** cruzamento de retorno (`retorno.py:560 cruzar_com_sinapse`); **4)** volumetria escalado × montado.
3. Meta sugerida: **80% de cobertura em `services/`** (com `pytest-cov` + `fail-under` no CI), sem exigir cobertura de código de UI.
4. Criar `tests/fixtures/` com 3 recortes anonimizados (produção, ativos, quebra) e testes de contrato: "com esta entrada, o fechamento do mês é X". Isso vale mais que 50 testes de sintaxe.

---

### 🟡 P2-1 — Dependências sem uso

Declaradas em `requirements.txt` e **sem nenhuma importação** no código: `duckdb`, `pydeck`, `matplotlib`, `chardet`, `streamlit-carousel`, `pytz`, `gspread-dataframe`, `gspread-formatting`, `gspread-pandas`, `google-api-python-client`, `google-auth-oauthlib`. Além disso, `google-auth` **é usado** (`gestao_ativos.py:20`) mas **não está declarado** — depende de vir junto com `gspread`/`google-auth-oauthlib`, o que quebra se alguém remover um deles.

**Ação:** remover as 11 não usadas; declarar `google-auth>=2.28,<3.0` explicitamente. Ganho: deploy mais rápido no Community Cloud, menos CVEs para monitorar. Se `duckdb` foi previsto para joins pesados, decida: **usar** (ver P2-2) ou remover.

---

### 🟡 P2-2 — Falta uma camada de dados única

**Evidência:** cada página tem seu carregador — `streamlit_gsheets.GSheetsConnection` (`consultivo.py:151`), `carregar_planilha_gsheets_csv` (`indicadores.py:588`, `p_atendimento.py:448`), download HTTP com fallback gviz (`dashboard_meta.py:591`, `quebra_geral.py:709`), e TTLs que variam (0, 300, 600, 3600, 86400, sem TTL) sem critério documentado.

**Impacto:** a mesma planilha é baixada 3-4 vezes com regras diferentes; um problema de frescor aparece em uma página e não em outra; impossível medir quanto o app consome da API do Google.

**Proposta:**

```python
# services/dados/repositorio.py
@dataclass(frozen=True)
class FonteDados:
    nome: str
    url: str
    ttl: int
    obrigatoria: bool = True

FONTES = (
    FonteDados("ativos", URL_ATIVOS_CSV, ttl=300),
    FonteDados("producao", URL_PROD_XLSX, ttl=600),
    FonteDados("consultivo", URL_CONS_DOWNLOAD, ttl=600),
)

@st.cache_data(ttl=..., show_spinner="Sincronizando produção…")
def carregar(fonte: FonteDados) -> pd.DataFrame: ...
```

Benefícios imediatos: TTL em um só lugar (corrige o "0 s aqui, 1 h ali"), ponto único para métricas de latência/falha (alimenta o relatório de ingestão do §4.E) e um único lugar para trocar a fonte quando o volume crescer. Para os joins pesados entre produção × ativos × quebra, `duckdb` sobre os DataFrames já carregados é a evolução natural — e resolveria agregações hoje feitas linha a linha em pandas dentro das páginas.

---

### 🟡 P2-3 — Padronização de projeto ausente

Não existem `pyproject.toml`, `.streamlit/config.toml`, `.pre-commit-config.yaml` nem lockfile. Sugestão:

```toml
# pyproject.toml — metadata + ferramentas em um só lugar
[project]
name = "painel-totale"
requires-python = ">=3.11"

[tool.pytest.ini_options]
addopts = "-q --strict-markers"
testpaths = ["tests"]

[tool.coverage.run]
source = ["components", "services", "robo", "config"]
omit = ["*/tests/*"]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "B", "UP", "SIM", "PL"]
ignore = ["E402"]
```

```toml
# .streamlit/config.toml — comportamento do app versionado
[theme]
primaryColor = "#012869"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F1F5F9"
textColor = "#334155"

[server]
maxUploadSize = 50
enableStaticServing = false

[browser]
gatherUsageStats = false
```

Complementos: `.pre-commit-config.yaml` com `ruff` + `ruff-format` + os scripts de `tests/`; e geração de lockfile (`uv pip compile requirements.txt -o requirements.lock`) para eliminar surpresa de build no Cloud. Acrescente `B`, `UP`, `SIM` e `PL` ao Ruff de forma incremental — hoje o conjunto `E4/E7/E9/F/I` não pega `bugbear` nem `pylint`.

---

### 🟡 P2-4 — Higiene do README e da documentação

- `README.md:92,99,106` referencia `docs/screenshots/dashboard.png`, `hierarquia.png` e `assinatura.png` — **os arquivos não existem** (o diretório `docs/` não estava versionado). As três imagens aparecem quebradas na página do GitHub, que é a primeira impressão do projeto.
- A árvore de `## 📁 Estrutura do Projeto` não menciona `docs/` (agora existente) — `test_higiene_repositorio.py` valida README→repo, mas não repo→README; vale inverter o teste também para o diretório `docs/`.
- `SIDEBAR_DOCUMENTATION.md` na raiz competiria melhor dentro de `docs/`.

---

## 4. Sugestões de relatórios (novas páginas/módulos)

Os relatórios abaixo foram desenhados em cima do que o repo **já coleta** (produção, ativos, consultivo, quebra, rotas, volumetria, primeira atendimento, retorno TOA↔Sinapse, metas) e do design system existente. Esforço em dias-pessoa.

| # | Relatório | Pergunta que responde | Dados que já existem | Esforço |
|---|---|---|---|:--:|
| A | SLA & Aging de O.S. | "O que está vencendo e o que vamos furar amanhã?" | produção (datas, tipo, base) | 3 |
| B | Produtividade por hora de jornada | "Quem produz de verdade por hora escalada?" | produção + primeira atendimento | 3 |
| C | Fix rate / 1ª tentativa resolvida | "Quanto retrabalho a instalação está gerando?" | produção + retorno | 4 |
| D | Coorte de quebra (sobrevivência) | "Qual safra de instalações está morrendo mais?" | quebra + ativos | 4 |
| E | Qualidade de dados & saúde da ingestão | "Posso confiar no número de hoje?" | saude_dados + robô + status_fontes | 2 |
| F | Capacidade × demanda (S&OP diário) | "Vamos zerar a fila com a equipe de amanhã?" | produção + escalados | 4 |
| G | Eficiência de rota e deslocamento | "Onde a quilometragem está sendo queimada?" | rota_* + malha geobr já cacheada | 4 |
| H | Metas com projeção probabilística | "Qual a chance de bater a meta do mês?" | metas + produção diária | 3 |
| I | Custo por O.S. / margem por base | "Quanto custa cada visita e onde sobra margem?" | produção + tabela de custos (nova) | 5 |
| J | People analytics (turnover e aprendizagem) | "Quem está saindo e quem ainda não engrenou?" | ativos + produção + desligados | 4 |
| K | Auditoria & LGPD | "Quem acessou o quê, e o que precisamos apagar?" | log_auditoria | 3 |
| L | Boletim semanal executivo (PDF 1 página) | "Resumo da base X para a diretoria em 1 minuto" | todos | 3 |

### A) SLA & Aging de O.S. — *o relatório de maior valor imediato*

- **Problema:** prazo estourado é percebido quando o cliente reclama; não há fila envelhecendo visível por base/tipo.
- **KPIs:** % de O.S. concluídas no prazo (prazos por tipo de serviço como parâmetro de configuração), tempo médio e **P90** de execução (média esconde a cauda), *aging* do backlog em faixas (0-1, 2-3, 4-7, 8-15, >15 dias), O.S. em risco (vencer nas próximas 24/48 h), reaberturas.
- **Gráficos:** barras empilhadas de aging por base; heatmap base × faixa; linha de % no prazo com faixa de meta; tabela drill-down com semáforo (reusar `render_table_html` e `render_kpi_grid`).
- **Onde encaixar:** nova página `pages/sla_aging.py` no grupo "Disparos Diários"; KPIs do topo reaproveitam `components/metricas_executivas.py`.

### B) Produtividade por hora de jornada (não por O.S. absoluta)

- **Problema:** o painel atual mede volume e pontos; um técnico com muitos pontos pode estar produzindo menos por hora de jornada, e a escala é distribuída por volume, não por eficiência.
- **KPIs:** pontos/O.S. por **hora de jornada**; utilização = horas em execução ÷ horas escaladas; tempo ocioso médio entre O.S.; primeira O.S. do dia (o `p_atendimento` já calcula o "madrugador" — transformar em indicador); dispersão por técnico (P90 − P50).
- **Gráficos:** scatter pontos × horas com reta de referência; distribuição (boxplot) por base; ranking com banda de variação; alerta automático para utilização < 60% (componente de alertas já existe).
- **Cuidado metodológico:** normalizar por mix de dificuldade (segmento ND/Migração/PME) — sem isso o ranking pune quem atende o serviço mais pesado. Documentar em "Metodologia", no padrão já usado nas páginas.

### C) Fix rate / Primeira Tentativa Resolvida

- **Problema:** o retorno (TOA ↔ Sinapse) hoje é auditável, mas não é ligado a quem instalou e a quanto custou.
- **KPIs:** % de contratos sem retorno em 7/30 dias após a instalação; retrabalho por técnico e por monitor; custo do retrabalho (nº de retornos × custo médio por visita — parâmetro configurável); concentração (Pareto dos 20% que geram 80% dos retornos); motivo do retorno por código.
- **Gráficos:** funil instalação → retorno em 7/30/60 dias; heatmap técnico × semana; Pareto; série temporal com meta.
- **Insumo:** `pages/retorno.py:560` (`cruzar_com_sinapse`) já faz o cruzamento — extrair para `services/dominio/retrabalho.py` e reutilizar (mata o P1-3 e o P1-4 no mesmo movimento).

### D) Coorte de quebra (análise de sobrevivência)

- **Problema:** a quebra atual é um número do mês; a pergunta de negócio é *quando* o contrato morre após a instalação e se a qualidade da instalação influencia.
- **KPIs:** curva de sobrevivência por **safra** (mês de instalação) — Kaplan-Meier; churn por idade do contrato (hazard); quebra por segmento e motivo (incluindo a aba "SEM REGISTRO" já existente, que é um indicador de qualidade de dados); % da quebra ocorrida nos primeiros 90 dias (proxy de problema de instalação).
- **Gráficos:** KM com uma linha por safra; heatmap safra × mês; treemap de motivos; contribuição da quebra por base.
- **Valor:** conecta-se diretamente ao relatório C — "safra com mais retorno em 7 dias é a que mais quebra em 90" é a frase que muda processo.

### E) Qualidade de dados & saúde da ingestão (observabilidade)

- **Problema:** já existem `saude_dados.py` (frescor/consistência) e `alertas_automaticos.py`, mas faltam **histórico e SLO**. Quando o número do dia está estranho, ninguém sabe se é operação ou ingestão.
- **KPIs:** frescor por fonte (min desde o último sucesso) com SLO de 15/60 min; taxa de sucesso de sincronização (7 dias); latência de leitura por fonte; % de nulos por coluna crítica (contrato, base, datas, técnico); duplicidade de contrato/O.S.; nº de linhas por carga (variação > 30% = alerta); atraso do robô local (arquivo mais recente vs. esperado).
- **Gráficos:** heatmap coluna × dia (% nulos); linha de frescor com faixa de SLO; barras de sucesso/falha por fonte; tabela de incidentes com causa.
- **Por que é um relatório forte:** é o tipo de página que quase ninguém tem e que demonstra maturidade de engenharia de dados — vira o "termômetro de confiança" do portal.

### F) Capacidade × demanda (S&OP operacional diário)

- **Problema:** a escala é montada por experiência; a fila do dia seguinte é descoberta no dia seguinte.
- **KPIs:** O.S. abertas por dia (por tipo, por base) vs capacidade (técnicos escalados × produtividade média ajustada por dia útil — `holidays` já está disponível em `qtde_os.py`); dias projetados para zerar o backlog; produtividade necessária para cumprir o prazo; folga/deficit por base com semáforo.
- **Gráficos:** área demanda vs capacidade com projeção de 15 dias; gauge de folga; waterfall de alocação sugerida por base; cenário what-if (slider de técnicos alocados → impacto na fila).

### G) Eficiência de rota e deslocamento

- **Problema:** `rota_inicial` já plota mapa com a malha `geobr` cacheada (`.streamlit_cache/geo_sp_2022.parquet`), mas não mede o custo do deslocamento.
- **KPIs:** O.S. por rota/turno; densidade de atendimentos por região (heatmap); dispersão geográfica dos atendimentos de um mesmo técnico; índice de proximidade (distância média entre O.S. consecutivas de um turno); % de O.S. fora da área de concentração; tempo estimado de deslocamento.
- **Gráficos:** mapa de calor (folium/pydeck), boxplot de dispersão por base, Pareto de bairros/municípios, "rota ideal × rota executada" quando houver sequência.
- **Evolução:** com coordenadas por O.S., otimização de sequência (clássico TSP com `networkx`) e ganho estimado em km/horas — argumento financeiro direto para a diretoria.

### H) Metas com projeção probabilística

- **Problema:** a projeção atual (`dashboard_meta`) é um número único; qualquer número único será tratado como promessa.
- **KPIs:** probabilidade de bater a meta (%), faixa P10-P90 de fechamento, pontos/dia necessários vs. ritmo observado, dia projetado de atingimento, contribuição por base para o risco total.
- **Gráficos:** leque de cenários (fan chart) sobre a série diária; gauge com P(meta); barras por base com intervalo; tabela "o que precisa acontecer" (pontos/dia por base).
- **Método:** bootstrap dos ritmos diários históricos (200-1000 simulações no `numpy`, instantâneo no Streamlit). Documentar premissa e limitação — o repo já tem bom histórico de documentar método.

### I) Custo por O.S. / margem por base

- **Problema:** a operação é gerida por volume e prazo; ninguém sabe qual serviço dá lucro e qual dá prejuízo.
- **KPIs:** custo por O.S. (hora técnica × custo-hora + deslocamento + retrabalho + hora extra); custo por ponto; receita por segmento; margem por base e por segmento (ND/Migração/PME); payback de hora extra (R$ de hora extra ÷ R$ de receita adicional); custo do retrabalho (liga com C).
- **Requer:** uma planilha de parâmetros (custo-hora por base, custo por km, receita por tipo de serviço) — tabela de configuração simples, versionada fora do código.
- **Gráficos:** waterfall de composição do custo; barras de margem por base; scatter custo × receita; semáforo de serviços deficitários.
- **Valor:** é o relatório que faz a operação deixar de ser centro de custo "cego" — alto impacto executivo.

### J) People analytics: turnover, absenteísmo e curva de aprendizagem

- **KPIs:** turnover por base/monitor (mensal e acumulado 12 m, usando `desligados` + `Data_Desligamento`); absenteísmo (dias escalados sem produção — cuidado com a metodologia, `resumo_frequencia` já alerta para não inferir ausência); **curva de aprendizagem**: dias até o técnico atingir 80% da mediana da base, por coorte de admissão; risco de saída (quedas de produtividade + faltas + tempo de casa) como sinal, nunca como decisão.
- **Gráficos:** linhas de coorte de aprendizagem; boxplot de produtividade por faixa de tempo de casa; turnover por base; tabela de atenção com contexto.
- **Cuidado:** este relatório precisa de política de uso — ranking de produtividade individual só com contexto de mix, e sempre agregado em comunicações amplas. Explicitar isso na página é o que evita uso indevido.

### K) Auditoria & LGPD

- **Problema:** `log_auditoria` registra Data/Usuário/Perfil/Ação/Alvo/Detalhe, mas não há relatório de uso nem política de retenção — e o app carrega dados pessoais (nome, login, RE).
- **KPIs:** ações por usuário/perfil (série temporal); exportações realizadas (quem baixou o quê — hoje não é registrado: **sugerido registrar**); alterações de cadastro por dia; primeiro/último acesso; contas sem acesso há X dias (candidatas a revogação); retenção (linhas mais antigas que a política); mascaramento em exportações.
- **Gráficos:** linha de ações por dia; top alvos alterados; tabela de evidências exportável em PDF (compliance).
- **Ações de conformidade:** registrar toda exportação (usuário, página, filtros, nº de linhas) no log; mascarar dados pessoais nas exportações para perfis não-admin; definir retenção (ex.: 24 meses) e expurgo agendado; documentar base legal e finalidade na própria página.

### L) Boletim semanal executivo (PDF de 1 página)

- **Problema:** a diretoria consome os números em reunião, não navegando no portal.
- **Entregável:** 1 página por base com produção vs meta, tendência (D-1, W-1), quebra dos 7 dias, top 3 alertas e ação recomendada; gerado por `reportlab` (já é dependência e já é usado em `quebra_unificada.py`) e disponível em botão de download por base, evoluindo para envio automático semanal.
- **Ganho de portfólio corporativo:** transforma o portal de "painel que precisa ser aberto" em rotina de gestão.

---

## 5. Ajustes já aplicados nesta análise

| Arquivo | Mudança | Motivo |
|---|---|---|
| `tests/test_sintaxe.py` | `IGNORADOS` alinhado ao dos demais testes (`.venv-check`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache`, `node_modules`) | **Bug real:** o guarda varria `site-packages` e falhava com *"Marcadores de conflito de merge encontrados"* sempre que o ambiente virtual tinha nome diferente de `.venv` (ex.: `.venv-check`, usado pelo próprio `.gitignore:181`). Falso positivo que quebra o CI sem causa no código. Reproduzido e validado: antes falhava com o venv renomeado, agora passa |
| `.gitignore` | Adicionado `.ruff_cache/` | Único cache de ferramenta ausente da lista (`.pytest_cache/`, `.mypy_cache/` e `usuarios.db` já constavam) |

Verificação após as mudanças: `ruff check .` → *All checks passed*; `pytest -q` → **66 passed**; `python tests/test_sintaxe.py` com o venv renomeado → 6/6.

> O `.gitignore` do projeto já era abrangente — inclusive para `usuarios.db`, caches de teste e ambientes virtuais. Não havia vazamento de banco ou credencial na árvore versionada.

---

## 6. Roadmap priorizado

**Onda 1 — Segurança (1 semana)**
1. Gate de autenticação central + logout + expiração de sessão (P0-1); testar em ambiente de staging com secrets espelhados.
2. Remover IDs reais do código e falhar explicitamente sem secret (P0-2); revisar compartilhamento das planilhas.
3. Decidir e alinhar a licença (P0-3).
4. Excluir `pages/login.py` + `usuarios.db` (P0-4).
5. Registrar exportações no `log_auditoria` (base do relatório K).

**Onda 2 — Integridade e confiança nos dados (2 semanas)**
6. Escrita por linha + validação otimista + `_fetch.clear()` antes de escrever (P1-1).
7. Backup diário automático das planilhas críticas (Action agendada).
8. Camada de dados única com TTL padronizado + métricas de latência (P2-2).
9. Página de **Qualidade de dados & saúde da ingestão** (relatório E) — ela dá visibilidade imediata ao ganho da onda.

**Onda 3 — Consolidação de código (2-3 semanas)**
10. Extrair domínio para `services/dominio/` página a página, começando por `retorno` e `volumetria` (P1-3), com testes por função (P1-4).
11. Unificar o Design System e remover as cópias locais com teste-guarda (P1-2).
12. `pyproject.toml` + `.streamlit/config.toml` + pre-commit + lockfile (P2-3); limpar dependências (P2-1).

**Onda 4 — Valor analítico (3-4 semanas)**
13. Relatórios **A (SLA/Aging)**, **B (produtividade/hora)** e **C (fix rate)**.
14. Relatórios **H (projeção probabilística)** e **L (boletim PDF)**.
15. Relatórios **D (coorte de quebra)** e **I (custo/margem)** — exigem parâmetros de negócio novos.

---

## 7. Checklist de aceite (Definition of Done) para qualquer mudança

- [ ] `ruff check .` limpo e `pytest -q` verde antes do PR.
- [ ] Nenhum `st.*` dentro de `services/dominio/` (regra verificável por teste).
- [ ] Nenhuma definição nova de `render_*` fora de `components/`.
- [ ] Toda leitura de dados usa o repositório único (TTL definido na fonte).
- [ ] Toda escrita no Sheets é por linha, com invalidação de cache e validação otimista.
- [ ] Todo número exibido tem fonte, data de referência e método acessíveis na própria página.
- [ ] Exportação de dados com pessoal identificável respeita o perfil do usuário.
- [ ] Mudança de regra de negócio acompanha teste com caso real anonimizado em `tests/fixtures/`.

---

### Observação final

O maior risco deste projeto não é técnico, é de **percepção**: um painel corporativo bonito, com CI verde e design system próprio, que expõe dados de colaboradores em URL pública. Resolvendo a Onda 1, o restante das melhorias passa a ser evolução — não correção de dívida escondida.
