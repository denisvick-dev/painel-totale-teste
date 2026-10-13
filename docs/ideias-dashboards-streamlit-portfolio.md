# 5 Ideias de Dashboards Streamlit para Portfólio de Dados

> Documento de planejamento — escolha, priorize, construa e publique.
> Cada ideia foi pensada para (a) resolver um problema de negócio real, (b) usar **dados públicos e gratuitos**, e (c) demonstrar um conjunto diferente de habilidades técnicas.

**Contexto de aproveitamento:** o Painel TOTALE deste repositório já tem o que a maioria dos portfólios não tem — design system (`components/dashboard_kit.py`), fábricas de gráficos Plotly, exportação CSV/Excel, insights automáticos, testes com `AppTest` e CI no GitHub Actions. Qualquer uma das ideias abaixo pode nascer reaproveitando esse kit (crie um repositório público separado e leve o que fizer sentido). Isso encurta o caminho e eleva o padrão visual desde o dia 1.

**Stack base recomendada (já instalada neste repo):** Streamlit ≥ 1.52 · pandas · Plotly · Altair · DuckDB · geopandas + geobr + folium + pydeck · requests · pytest + AppTest · GitHub Actions.

---

## Índice

| # | Ideia | Tema | Dificuldade | Habilidades que destacam |
|---|-------|------|-------------|--------------------------|
| 1 | 🌾 Radar de Risco Climático & Safra | Agro / clima | Média | APIs sem chave, séries climáticas, geoespacial |
| 2 | 🕵️ Torre de Controle das Compras Públicas | Integridade / setor público | Média-alta | API com token, detecção de anomalias, grafos, NLP |
| 3 | ⚡ Gêmeo Digital da Conta de Energia | Energia / finanças | Alta | Séries horárias em DuckDB, simulador financeiro, Monte Carlo |
| 4 | 🫁 Sala de Situação da Saúde Pública | Saúde / epidemiologia | Alta | Nowcasting, incerteza estatística, storytelling |
| 5 | 🚌 Auditor de Acessibilidade do Transporte | Mobilidade / cidades | Média-alta | GTFS, OSMnx, isócronas, otimização |

**Bônus** ao final: 2 ideias extras (Previdência atuarial e Inflação pessoal) para quem quiser um ângulo mais "finanças pessoais".

---

## 1. 🌾 Radar de Risco Climático & Safra ("o dashboard que avisa antes da perda")

**Pitch:** um painel que cruza clima histórico + previsão + produção agrícola municipal para dizer, em linguagem de negócio, *quem vai perder safra, onde e quanto* — com alertas semanais.

### Problema de negócio

- **Quem sofre hoje:** cooperativas agrícolas, tradings, seguradoras de seguro rural (Proagro e privado), bancos com carteira de crédito agrícola e revendas de insumos.
- **A dor:** decisões de crédito, precificação de seguro e logística de compra são tomadas com relatórios defasados e planilhas manuais; ninguém consegue olhar 5.500 municípios ao mesmo tempo e antecipar um evento de seca ou geada.
- **Pergunta que o painel responde:** "Qual município produtor de soja/milho/café está entrando em estresse hídrico nas próximas 2 semanas, e qual é a exposição financeira estimada?"

### KPIs e gráficos recomendados

| KPI | Como calcular | Visual recomendado |
|---|---|---|
| Índice de severidade de seca (SPI/percentil) | Precipitação acumulada vs. distribuição histórica (mesmo período, 20–30 anos) | Mapa coroplético municipal (faixas de risco) |
| Dias consecutivos sem chuva | Run-length sobre série diária | Heatmap município × semana |
| Déficit hídrico acumulado (%) | (chuva atual − chuva normal) ÷ chuva normal | Série temporal com banda de normalidade climatológica |
| Graus-dia acumulados (GDD) | Σ [(Tmáx+Tmín)/2 − Tbase] no ciclo | Linha com limite de ciclo da cultura |
| Janela de plantio/colheita útil | Dias aptos (chuva + umidade do solo) | Bullet chart por município |
| Exposição financeira em risco | área plantada × produtividade esperada × preço (CONAB) | Barras + waterfall de perda estimada |
| Score de risco composto (0–100) | Ranking normalizado dos índices acima | Ranking com semáforo + alertas |

**Recursos Streamlit para brilhar:** `st.map`/`pydeck` para o mapa de risco, `st.segmented_control` para alternar cultura/UF, `st.slider` para simular cenário de chuva (what-if), `st.fragment` para o bloco de alertas atualizar sem recarregar a página, `st.download_button` para o boletim.

### Fontes de dados públicas (todas gratuitas)

| Fonte | Link | Observações técnicas |
|---|---|---|
| Open-Meteo (previsão + archive) | https://open-meteo.com/ · arquivo: `https://archive-api.open-meteo.com/v1/archive` | **Sem chave de API**, histórico desde 1940, ~10 mil requisições/dia (fair use). CORS desabilitado → chame do servidor e cacheie com `st.cache_data(ttl="6h")` |
| NASA POWER | https://power.larc.nasa.gov/docs/services/api/temporal/daily/ | Sem chave; ideal para normais climatológicas de longo prazo |
| INMET — dados históricos | https://portal.inmet.gov.br/dadoshistoricos | ZIPs anuais por estação; boa fonte "oficial brasileira" |
| IBGE — Produção Agrícola Municipal (SIDRA 1612) | https://sidra.ibge.gov.br/tabela/1612 · API: https://apisidra.ibge.gov.br/ | Área, produção e rendimento por município/cultura; use `c81` para filtrar produto |
| CONAB — séries históricas de safra | https://www.conab.gov.br/info-agro/safras/serie-historica-das-safras | Safra + preços; base para a exposição financeira |
| Malhas municipais (geobr) | https://github.com/ipeaGIT/geobr | `geobr.read_municipality()` — já é dependência deste repo |
| Kaggle (complementar) | https://www.kaggle.com/datasets | Datasets de produtividade agrícola e clima para enriquecer o modelo |

### Diferencial "wow"

Alertas automáticos gerados por regra (ex.: "3 municípios do Mato Grosso entraram em risco alto") + **copiloto LLM** (`st.chat_message`) que traduz o gráfico em recomendação de negócio: "revise a carteira de crédito de X cooperativas nesta semana". Feche com uma página **Metodologia** explicando as premissas — isso é o que separa portfólio júnior de sênior.

### Estrutura sugerida

```
radar-agro/
├── app.py                    # home + st.navigation
├── pages/
│   ├── 1_mapa_de_risco.py
│   ├── 2_serie_e_alertas.py
│   └── 3_simulador_de_cenario.py
├── src/
│   ├── ingestao/             # clientes das APIs + camada bronze
│   ├── transformacao/        # DuckDB + parquet (silver/gold)
│   ├── indicadores/          # funções puras e testáveis (SPI, GDD)
│   └── alertas/
└── tests/
```

---

## 2. 🕵️ Torre de Controle das Compras Públicas ("o detector de sobrepreço")

**Pitch:** um painel de integridade que pega contratos e licitações federais, compara preços com a referência oficial e aponta onde o dinheiro público está sendo comprado com sobrepreço — em cima de uma API real do governo.

### Problema de negócio

- **Quem sofre hoje:** órgãos de controle (CGU, TCEs), jornalistas de dados, gestores públicos, comissões de licitação e até fornecedores que querem se posicionar melhor.
- **A dor:** auditar milhares de contratos manualmente é inviável; sinais de risco (sobrepreço, concentração de fornecedor, contratos com empresas sancionadas, aditivos recorrentes) ficam escondidos em bases enormes.
- **Pergunta que o painel responde:** "Quais 20 contratos do último trimestre têm maior probabilidade de risco e por quê?"

### KPIs e gráficos recomendados

| KPI | Como calcular | Visual recomendado |
|---|---|---|
| Sobrepreço unitário (%) | preço unitário contratado vs. mediana do Painel de Preços (itens iguais/similares) | Scatter quantidade × valor em escala log (outliers saltam) |
| Taxa de dispensa de licitação | dispensas ÷ total de compras | Série temporal por mês + meta |
| Concentração de fornecedores (HHI) | Σ participação² por órgão | Barras de ranking + curva de Pareto |
| % de contratos com aditivos | contratos com aditivo ÷ total | Donut + evolução |
| Empresas sancionadas contratadas | cruzamento CNPJ com CEIS/CNEP | Tabela com semáforo + alerta destacado |
| Valor contratado por habitante | valor ÷ população do município (IBGE) | Mapa por UF/município |
| Tempo entre edital e assinatura | data edital → data assinatura (mediana/P90) | Boxplot por órgão/modalidade |

**Recursos Streamlit para brilhar:** `st.dataframe` com `column_config` (barra de risco, links para o contrato), grafo órgão–fornecedor com `networkx` + Plotly, `st.popover` com o "dossiê" de cada contrato, exportação de dossiê em PDF (`reportlab`), NLP simples (`scikit-learn`/regex) para padronizar objetos de contrato e agrupar itens comparáveis.

### Fontes de dados públicas

| Fonte | Link | Observações técnicas |
|---|---|---|
| API do Portal da Transparência (CGU) | Base: `https://api.portaldatransparencia.gov.br/api-de-dados` · token: https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email | **Token gratuito por e-mail**, enviado no header `chave-api-dados`. Tem limite de requisições → página com paginação, cacheie em parquet e agende ingestão |
| Compras.gov.br — dados abertos | https://dadosabertos.compras.gov.br/ | Catálogo + API de itens e preços (base para o "preço de referência") |
| Painel de Preços | https://www.gov.br/compras/pt-br/painel-de-precos | Preços praticados pelo governo federal — referência para o cálculo de sobrepreço |
| CEIS / CNEP (empresas sancionadas) | Endpoints `/ceis` e `/cnep` na mesma API da CGU | Cruzamento por CNPJ; gera o KPI de integridade mais impactante |
| Dados Abertos da Câmara e do Senado | https://dadosabertos.camara.leg.br/ · https://legis.senado.leg.br/dadosabertos/ | Emendas e proposições; bom para cruzar "quem pediu" × "quem recebeu" |
| IBGE (população / PIB municipal) | https://servicodados.ibge.gov.br/api/v3/agregados/ | Denominadores para os indicadores normalizados |
| dados.gov.br | https://dados.gov.br/ | Catálogo para encontrar bases complementares estaduais/municipais |

### Diferencial "wow"

Um bloco de **"sinais de risco" explicáveis** (score com os fatores que mais contribuíram — tipo um mini SHAP, mesmo que por regras) e um botão **"Gerar dossiê"** que exporta um PDF com o contrato, o preço de referência, a diferença e a fonte. Publicar com dados reais e citar a fonte em cada gráfico é o que dá credibilidade ao projeto.

### Estrutura sugerida

```
integridade-compras/
├── app.py
├── pages/
│   ├── 1_panorama.py
│   ├── 2_alertas_de_risco.py
│   ├── 3_dossie_do_contrato.py
│   └── 4_metodologia.py
├── src/ingestao/  src/regras/  src/nlp/  src/relatorios/
└── data/          # parquet versionado por data de extração
```

---

## 3. ⚡ Gêmeo Digital da Conta de Energia ("o simulador do mercado livre")

**Pitch:** um simulador que mostra quanto a sua empresa pagaria de energia no mercado cativo vs. livre, com PLD real, tarifas da ANEEL e cenários probabilísticos — o dashboard que um CFO realmente usaria.

### Problema de negócio

- **Quem sofre hoje:** gestores de energia de indústrias, redes de varejo e escritórios, além de consultorias de eficiência energética.
- **A dor:** desde a abertura do mercado livre para consumidores de menor porte, milhares de empresas precisam decidir *se migram*, *quanto contratam* e *como se protegem da volatilidade do PLD* — quase sempre com uma planilha e muita intuição.
- **Pergunta que o painel responde:** "Dado o meu perfil de consumo horário, qual contrato (volume × preço × flexibilidade) minimiza meu custo esperado e qual é meu pior cenário?"

### KPIs e gráficos recomendados

| KPI | Como calcular | Visual recomendado |
|---|---|---|
| PLD por submercado | série oficial CCEE (horário/diário/semanal) | Linha com faixas de patamar (acionamento térmico) |
| Custo total R$/MWh (mercado livre) | energia + encargos + demanda + tributos | Waterfall de composição da fatura |
| Economia vs. mercado cativo | custo cativo − custo livre (R$ e %) | Barras comparativas + gauge de atingimento |
| Exposição ao spot | volume descontratado × PLD | Área empilhada + semáforo |
| Preço médio ponderado contratado | Σ (volume × preço) ÷ Σ volume | Cartão de KPI + linha |
| Pior cenário / VaR do custo mensal | simulação Monte Carlo dos preços | Leque de cenários (fan chart) + histograma |
| Nível dos reservatórios (EAR) e ENA | dados do ONS por subsistema | Linha com faixas históricas mín./máx. |
| Flags de bandeira tarifária | ANEEL por mês de referência | Timeline colorida |

**Recursos Streamlit para brilhar:** `st.slider` de volume/perfil de consumo, `st.data_editor` para montar a curva de carga horária, `st.tabs` (Cativo × Livre × Cenários), `st.cache_data` para as séries horárias (alta cardinalidade) com **DuckDB** fazendo as agregações, `st.metric` com delta de economia.

### Fontes de dados públicas

| Fonte | Link | Observações técnicas |
|---|---|---|
| CCEE — Dados Abertos (PLD) | https://dadosabertos.ccee.org.br/ | Conjuntos `PLD_MEDIA_HORARIA`, `_DIARIA`, `_SEMANAL`, `_MENSAL` em CSV — o coração do projeto |
| ONS — Dados Abertos | https://dados.ons.org.br/ | Carga, ENA (energia natural afluente) e EAR (armazenamento) por subsistema |
| ANEEL — Dados Abertos | https://dadosabertos.aneel.gov.br/ | Tarifas homologadas (Resolução 1.000), bandeiras tarifárias, unidades consumidoras |
| BCB — SGS | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json` (ex.: 433 = IPCA) | **Limites reais da API:** janela máxima de 10 anos por consulta e `/ultimos/{N}` limitado a 20 — use períodos explícitos |
| EPE — publicações e dados abertos | https://www.epe.gov.br/pt/publicacoes-dados-abertos | Cenários de preço e consumo para calibrar projeções |
| ANP — preços de combustíveis | https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos | CSV semanal de preços de gasolina/diesel/etanol — ótimo para comparar com o custo elétrico |
| Kaggle | https://www.kaggle.com/datasets | Bases históricas para validação do simulador |

### Diferencial "wow"

O **motor de simulação** é a estrela: contrato com volume mínimo, flexibilidade (swing), piso/teto e migração de mercado. Mostre a matemática na página de metodologia e um `st.expander("Como calculamos isso")` em cada resultado. Rodar Monte Carlo com 10 mil cenários dentro do Streamlit (com `numpy` vetorizado + cache) impressiona mais do que qualquer gráfico.

### Estrutura sugerida

```
gemeo-energia/
├── app.py
├── pages/
│   ├── 1_painel_de_precos.py
│   ├── 2_minha_conta.py        # upload da curva de carga + tarifa
│   ├── 3_simulador_de_contrato.py
│   └── 4_metodologia.py
├── src/ingestao/  src/mercado/  src/contratos/  src/simulacao/
└── db/               # DuckDB + parquet
```

---

## 4. 🫁 Sala de Situação da Saúde Pública ("nowcasting de surtos em tempo real")

**Pitch:** um painel de vigilância sindrômica que mostra o passado, corrige o atraso de notificação (*nowcasting*) e projeta as próximas semanas com intervalo de incerteza — o tipo de dashboard que faz um epidemiologista pedir o link.

### Problema de negócio

- **Quem sofre hoje:** secretarias de saúde, hospitais e gestores de leitos.
- **A dor:** os dados de SRAG chegam com atraso e correção retroativa; quando o surto "aparece" no gráfico, a capacidade já estourou. Sem tratar o atraso de notificação, qualquer decisão de leitos e insumos é feita olhando para o retrovisor.
- **Pergunta que o painel responde:** "Dado o que já foi notificado, qual é a real incidência de SRAG nas últimas 3 semanas e o que esperar para as próximas 4?"

### KPIs e gráficos recomendados

| KPI | Como calcular | Visual recomendado |
|---|---|---|
| Casos e óbitos por semana epidemiológica | agregação por `DT_SIN_PRI` (início de sintomas) | Série temporal com correção retroativa |
| Incidência por 100 mil habitantes | casos ÷ população (IBGE) | Mapa + small multiples por UF |
| Nowcasting da última semana | modelo de completude de notificação (delay) | Fan chart com intervalo de credibilidade |
| Taxa de positividade por vírus | positivos ÷ testados (SRAG, Covid, Influenza, VSR) | Área empilhada por vírus |
| Tendência (crescimento/queda) | variação % vs. semanas anteriores + limiar de alerta | Setas + cores (verde/amarelo/vermelho) |
| Detecção de surto (CUSUM/EWMA) | gráfico de controle estatístico | Linha com limites de controle |
| Perfil dos casos | pirâmide etária × sexo, comorbidades, UTI/ventilação | Pirâmide + heatmap de comorbidades |
| Atraso mediano de notificação | (data de notificação − início de sintomas) | Histograma/boxplot por semana |

**Recursos Streamlit para brilhar:** `st.metric` com delta colorido, `st.segmented_control` (Brasil/UF/regional), `st.tabs` (Panorama × Perfil × Método), **exportação de boletim semanal**, e um bloco obrigatório de **"limitações e incerteza"** — mostrar honestidade estatística é um diferencial enorme de portfólio.

### Fontes de dados públicas

| Fonte | Link | Observações técnicas |
|---|---|---|
| OpenDataSUS — SRAG (casos individuais) | https://dadosabertos.saude.gov.br/dataset/srag-2019-a-2026 | Arquivos anuais "congelados" + "banco vivo" atualizado **semanalmente**; há versões em **CSV e Parquet** (Parquet é ouro para Streamlit). API CKAN: `https://dadosabertos.saude.gov.br/api/3/action/package_show?id=srag-2019-a-2026` |
| InfoGripe (Fiocruz) | https://gitlab.procc.fiocruz.br/mave/repo (pasta `Dados/InfoGripe`) | Dados abertos semanais por faixa etária, sexo e vírus — referência nacional em nowcasting |
| DATASUS — TabNet | https://datasus.saude.gov.br/informacoes-de-saude-tabnet/ | Séries consolidadas para validação cruzada |
| CNES — leitos e hospitais | https://dadosabertos.saude.gov.br/dataset/hospitais-e-leitos | Denominador para taxa de ocupação de leitos |
| IBGE — população | https://servicodados.ibge.gov.br/api/v3/agregados/ | Numerador/denominador por município |
| Painéis do Ministério da Saúde | https://infoms.saude.gov.br/ | Comparação com números oficiais divulgados |

### Diferencial "wow"

Escolher **uma** técnica e executá-la bem, documentando os trade-offs: `INLA`/modelo Bayesiano hierárquico, `pymc` ou até um método simples de fator de correção (o famoso nowcasting de Noufaily et al.). Plote sempre o intervalo de incerteza — **isso é o que o mercado de dados valoriza e o que 95% dos portfólios não faz.** Feche com um "Boletim da semana" gerado em PDF.

### Estrutura sugerida

```
sala-situacao-saude/
├── app.py
├── pages/
│   ├── 1_panorama_nacional.py
│   ├── 2_nowcasting.py
│   ├── 3_perfil_dos_casos.py
│   └── 4_metodologia_e_limitacoes.py
├── src/ingestao/  src/epidemiologia/  src/nowcasting/  src/boletim/
└── data/     # parquet particionado por ano/UF
```

---

## 5. 🚌 Auditor de Acessibilidade do Transporte Público ("onde a cidade deixa gente para trás")

**Pitch:** um painel que calcula, a partir do GTFS oficial, **quantos empregos uma pessoa alcança em 30/45/60 minutos** a partir de qualquer bairro — e mostra o custo social do desenho atual da malha.

### Problema de negócio

- **Quem sofre hoje:** gestores de mobilidade, empresas decidindo onde abrir unidades, RH avaliando acessibilidade do local de trabalho, plataformas imobiliárias e ONGs de equidade urbana.
- **A dor:** as decisões são tomadas por mapa estático e opinião; não se mede o que importa — o **acesso a oportunidades** (emprego, saúde, educação), que é desigual dentro da mesma cidade.
- **Pergunta que o painel responde:** "Da periferia X, quantas oportunidades de emprego eu alcanço de transporte público em 45 minutos? E se eu morasse no bairro Y?"

### KPIs e gráficos recomendados

| KPI | Como calcular | Visual recomendado |
|---|---|---|
| Oportunidades alcançáveis (30/45/60 min) | isócrona via rede de transporte + pontos de emprego/POIs | Mapa de calor de acessibilidade (pydeck/folium) |
| Índice de acessibilidade por 100 mil hab. | oportunidades ponderadas ÷ população da área | Coroplético por bairro/município |
| Frequência e headway médio | partidas por hora por rota (GTFS `frequencies`/`stop_times`) | Heatmap hora × dia |
| Regularidade e cobertura | % de viagens dentro do intervalo previsto; % da população a ≤ 500 m de parada | Gauge + mapa de cobertura |
| Desigualdade de acesso | razão entre bairros de maior e menor renda | Barras comparativas + curva de Lorenz |
| Empregos por hora de deslocamento | oportunidades ÷ tempo total (incl. espera e caminhada) | Ranking por bairro |
| Custo social do gap | (acesso ideal − acesso real) × população afetada | Waterfall / cenário what-if |

**Recursos Streamlit para brilhar:** `pydeck` com camadas Arc/HexagonLayer, `folium` + `streamlit_folium` para isócronas, `st.slider` de tempo de viagem, `st.data_editor` para montar cenários ("adicionar 1 linha ligando A–B"), e animação temporal com `plotly.express` (hora do dia).

### Fontes de dados públicas

| Fonte | Link | Observações técnicas |
|---|---|---|
| Mobility Database (catálogo GTFS mundial) | https://mobilitydatabase.org/ | Encontra o feed GTFS oficial da sua cidade sem depender de cadastro em cada portal |
| SPTrans — GTFS e API Olho Vivo | https://www.sptrans.com.br/desenvolvedores/ | GTFS requer cadastro; a API Olho Vivo (posição dos ônibus em tempo real) é um diferencial e tanto |
| Dados abertos municipais | https://dados.prefeitura.sp.gov.br/ (e portais de Fortaleza, BH, Curitiba, Rio) | Feeds GTFS e bilhetagem para cidades específicas |
| OpenStreetMap (rede viária e POIs) | https://download.geofabrik.de/south-america/brazil.html · https://osmnx.readthedocs.io/ | Baixe a rede com OSMnx e calcule isócronas com `networkx` |
| IBGE — Censo 2022 (renda e domicílios) | https://censo2022.ibge.gov.br/ · API: https://servicodados.ibge.gov.br/api/v3/agregados/ | Cruzamento de acessibilidade × renda — é aqui que o projeto ganha impacto social |
| Ministério do Trabalho (RAIS/CAGED) | https://www.gov.br/trabalho-e-emprego/pt-br | Distribuição de empregos formais por bairro/município (proxy de "oportunidades") |
| geobr | https://github.com/ipeaGIT/geobr | Malhas de setores censitários, bairros e municípios — já é dependência deste repo |

### Diferencial "wow"

Um **comparador de cenários**: "e se eu adicionasse uma linha ligando o extremo sul ao centro empresarial?" — mostrando quantas pessoas ganhariam acesso a mais empregos. Some a isso um bloco de **equidade** (acessibilidade × renda) e você tem um storytelling urbano que nenhum portfólio genérico tem.

### Estrutura sugerida

```
acessibilidade-urbana/
├── app.py
├── pages/
│   ├── 1_mapa_de_acessibilidade.py
│   ├── 2_frequencia_e_cobertura.py
│   ├── 3_equidade.py
│   └── 4_cenarios.py
├── src/gtfs/  src/rede/  src/isocronas/  src/equidade/
└── data/    # GTFS bruto + grafo em parquet/geopackage
```

---

## 🎁 Bônus: 2 ideias extras (ângulo "finanças pessoais")

### Bônus A — 🧮 Simulador de Aposentadoria com Atuária de Verdade

- **Problema de negócio:** planejamento de aposentadoria é feito por chute; consultorias e planejadores precisam de um simulador com premissas atuariais reais. Público: planejadores financeiros, RH (previdência complementar) e o usuário final.
- **KPIs/visuais:** renda projetada, taxa de reposição (% do salário), anos de contribuição, leque de cenários Monte Carlo (inflação × retorno × longevidade), cascata de acumulação × desacumulação.
- **Fontes:** Tábuas Completas de Mortalidade do IBGE (https://www.ibge.gov.br/estatisticas/sociais/populacao/9126-tabuas-completas-de-mortalidade.html), Expectativas de mercado (Focus) e séries do BCB em https://dadosabertos.bcb.gov.br, dados do Tesouro Direto em https://www.tesourotransparente.gov.br/, Anuário Estatístico da Previdência Social (gov.br/previdencia).
- **Diferencial:** usar a tábua de mortalidade oficial brasileira (com `lifelib`/`pandas`) e simular 10 mil trajetórias — pouquíssimos portfólios fazem isso.

### Bônus B — 🛒 "Meu IPCA": inflação personalizada

- **Problema de negócio:** a inflação oficial não é a inflação de cada família; empresas e consumidores querem entender o custo de vida do próprio perfil (alimentação, transporte, energia).
- **KPIs/visuais:** IPCA pessoal vs. IPCA oficial, contribuição por item (waterfall), treemap de itens, poder de compra do salário mínimo, heatmap item × mês, comparativo de preços da gasolina por município.
- **Fontes:** SIDRA (IPCA 7060 — https://sidra.ibge.gov.br/tabela/7060 e séries do BCB, via SIDRA/apisidra), Cesta Básica do DIEESE (https://www.dieese.org.br/analisecestabasica/), preços de combustíveis da ANP (https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos), tarifas da ANEEL.
- **Diferencial:** o usuário monta a própria cesta com pesos (`st.data_editor`) e vê sua "inflação pessoal" contra a oficial — interatividade que viraliza.

---

## 🧭 Comparativo final e ordem de execução

| Ideia | Histórias de negócio | Dados | Dificuldade | Tempo estimado | Melhor para demonstrar |
|---|---|---|---|---|---|
| 1. Radar Agro | Forte | Gratuitos, sem chave | Média | 2–3 semanas | APIs + séries + geoespacial |
| 2. Compras Públicas | Muito forte | API com token gratuito | Média-alta | 3–4 semanas | Integridade + NLP + grafos |
| 3. Gêmeo de Energia | Forte | CSVs oficiais + série horária | Alta | 3–5 semanas | Engenharia de dados + simulação |
| 4. Nowcasting Saúde | Muito forte | Open data massivo | Alta | 3–5 semanas | Estatística + incerteza |
| 5. Acessibilidade Urbana | Forte | GTFS + OSM | Média-alta | 3–4 semanas | Geoespacial avançado + impacto social |

**Sugestão de sequência para o portfólio:**
1. **Comece pela 1 ou 5** — entregam impacto rápido e reaproveitam `geobr`/`folium` que você já domina.
2. **Depois a 2** — API com token + regras de negócio é o combo mais "contratável" para vagas de analytics engineering.
3. **A 3 ou 4 como projeto âncora** — escolha uma e vá fundo; um projeto profundo vale mais que três rasos. O portfólio vencedor é: 2 projetos rápidos e bem acabados + 1 projeto âncora com metodologia pública.

## ✅ Checklist de portfólio (vale para qualquer ideia)

- [ ] README com o problema de negócio, as fontes, a arquitetura e o link do app publicado (Streamlit Community Cloud é grátis).
- [ ] Cada gráfico com fonte e data de atualização visíveis na própria página.
- [ ] Página "Metodologia e limitações" — o item que mais diferencia portfolios.
- [ ] `st.cache_data` corretamente aplicado (granularidade e TTL) + ingestão agendada no GitHub Actions (este repo já tem CI em `.github/workflows/`).
- [ ] Testes com `streamlit.testing.v1.AppTest` (o Painel TOTALE já usa esse padrão).
- [ ] Dados em `parquet` + DuckDB em vez de CSV gigante versionado; `data/` no `.gitignore`.
- [ ] Exportação em CSV/Excel/PDF reaproveitando `components/dashboard_kit.py`.
- [ ] Acessibilidade mínima: contraste, `help=` nos campos, linguagem sem jargão.
- [ ] Um "copiloto" opcional com `st.chat_message` para explicar o dashboard em linguagem natural.

---

*Documento criado para apoiar a construção do portfólio de dados em Streamlit. Todas as fontes listadas são públicas e gratuitas; respeite os limites de requisição, cite a fonte e guarde uma cópia local dos dados para o app não depender de API disponível no momento da visita.*
