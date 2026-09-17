# One Piece TCG Lab

Laboratório local, auditável e preparado para IA para estudar decks de **ONE PIECE Card Game** sem limitar a análise às listas mais populares.

O projeto reúne catálogo de cartas, regras de construção, rotação, estatísticas de meta, matchups e partidas pessoais. A IA interpreta os resultados e formula hipóteses; o banco SQLite mantém fatos e validações determinísticas.

> Status do snapshot: **17/09/2026**. Catálogo inglês oficial completo até OP17.

## Sumário

- [Por que este projeto existe](#por-que-este-projeto-existe)
- [O que está pronto](#o-que-está-pronto)
- [Como funciona](#como-funciona)
- [Início rápido com Codex](#início-rápido-com-codex)
- [Instalação e uso pelo terminal](#instalação-e-uso-pelo-terminal)
- [Como analisar seu próprio deck](#como-analisar-seu-próprio-deck)
- [Como pedir melhoria do deck](#como-pedir-melhoria-do-deck)
- [Como usar com ChatGPT ou NotebookLM](#como-usar-com-chatgpt-ou-notebooklm)
- [Como compartilhar com outra pessoa](#como-compartilhar-com-outra-pessoa)
- [Comandos disponíveis](#comandos-disponíveis)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Dados incluídos](#dados-incluídos)
- [Como interpretar resultados](#como-interpretar-resultados)
- [Atualização dos dados](#atualização-dos-dados)
- [Testes](#testes)
- [Limitações](#limitações)
- [Direitos e uso dos dados](#direitos-e-uso-dos-dados)
- [Solução de problemas](#solução-de-problemas)

## Por que este projeto existe

Deckbuilding competitivo tende a convergir para listas publicadas em sites de top decks. Isso ajuda quem está começando, mas pode esconder cartas antigas, alternativas de baixo uso e respostas específicas para certos matchups.

O Lab foi criado para responder perguntas como:

- Meu deck é legal neste formato e nesta data?
- Quais são sua curva, defesa, quantidade de counter e principais fragilidades?
- Quais cartas legais combinam com o líder, mesmo sem aparecer nas listas populares?
- Uma carta está realmente pouco usada ou apenas não possuímos dados suficientes?
- Qual é a evidência disponível para determinado matchup?
- Como testar uma mudança sem confundir hipótese com resultado comprovado?
- O que minhas próprias partidas mostram ao longo do tempo?

Não existe modelo de machine learning próprio. Nesta fase, banco estruturado, regras determinísticas, estatística e uma LLM produzem resultado mais confiável e muito mais fácil de auditar.

## O que está pronto

- **2.785 números de carta** e **4.843 impressões**.
- **119 cartas OP17** e **142 líderes**.
- Nome, categoria, cores, custo, poder, vida, counter, raridade, atributos, traits, efeitos e triggers.
- Classificação de Rush, Blocker, Double Attack, Banish e Trigger, distinguindo keyword própria de keyword apenas concedida ou mencionada.
- Validação de 1 líder, 50 cartas principais, cores, limite de cópias, Block Icons, banimentos, restrições e pares proibidos.
- Standard EN com Blocks 2, 3, 4, 5 e X, vigente no snapshot desde 10/04/2026.
- Busca por cor, categoria, trait, texto, keyword, custo, counter e Block.
- Análise de curva, categorias, counter total, cartas sem counter, keywords e traits.
- Recomendação de candidatos legais fora da lista.
- Evidência de baixa utilização somente quando existe amostra real.
- Meta com 8 variantes representativas de simulador.
- 21 registros de matchup: 15 confrontos atuais de torneio e 6 recortes de simulador do Newgate.
- Intervalo Wilson de 95% para matchups.
- Registro separado de partidas pessoais.
- Exportação Markdown pronta para ChatGPT, Codex ou outra IA.
- 10 testes automatizados.

A auditoria detalhada está em [`docs/COMPLETION_AUDIT.md`](docs/COMPLETION_AUDIT.md).

## Como funciona

```text
Decklist OPTCGSim
       |
       v
Validação determinística
  cores, 50 cartas, cópias,
  rotação e restrições
       |
       v
Análise objetiva
  curva, counter, traits,
  keywords e fragilidades
       |
       v
Busca no catálogo legal completo
       |
       v
Uso competitivo + matchups
  fonte, data, ambiente e amostra
       |
       v
Contexto Markdown para a IA
       |
       v
Hipóteses, trocas e plano de testes
```

O arquivo `data/lab.db` é a fonte de verdade local. JSON guarda snapshots versionados de regras e meta. Markdown serve como documentação e pacote de contexto para IA.

## Início rápido com Codex

Esta é a forma recomendada.

1. Abra a pasta do projeto no Codex.
2. Coloque sua lista em `examples/meu_deck.txt`.
3. Faça uma pergunta em linguagem natural.

Exemplo:

> Analise `examples/meu_deck.txt` no Standard EN em 2026-09-17. Valide a lista, mostre curva, counter, fragilidades e cartas legais pouco usadas que combinam com o líder. Depois proponha versões conservadora, anti-meta e experimental.

Para matchup:

> Analise `examples/meu_deck.txt` contra `OP17-039 Rocks.D.Xebec`. Separe dados de simulador e torneio. Sugira entradas, saídas, plano de jogo e critérios de teste.

O arquivo [`AGENTS.md`](AGENTS.md) orienta o Codex a validar antes de recomendar, consultar o banco, não inventar efeitos e separar fatos, inferências e hipóteses.

## Instalação e uso pelo terminal

### Requisitos

- Python 3.11 ou superior.
- Git apenas se quiser clonar ou contribuir.
- Nenhuma biblioteca Python externa em tempo de execução.

### Clonar

```powershell
git clone https://github.com/P3robr/one-piece-tcg-lab.git
cd one-piece-tcg-lab
```

Como o repositório é privado, a pessoa precisa receber acesso no GitHub antes de clonar.

### Windows PowerShell

```powershell
$env:PYTHONPATH = "src"
python -m optcg_lab status data/lab.db
```

### macOS ou Linux

```bash
export PYTHONPATH=src
python3 -m optcg_lab status data/lab.db
```

Não é necessário instalar o pacote. Opcionalmente:

```powershell
python -m pip install -e .
```

Depois da instalação editável, `PYTHONPATH` deixa de ser necessário.

## Como analisar seu próprio deck

Crie `examples/meu_deck.txt` no formato OPTCGSim:

```text
1xOP17-001
4xOP17-002
4xOP17-003
2xOP17-012
```

Linhas duplicadas são somadas. Comentários iniciados por `#` são ignorados.

Uma lista completa deve conter:

- exatamente 1 líder;
- exatamente 50 cartas no deck principal;
- no máximo 4 cópias de cada número, salvo restrição mais severa;
- somente cores permitidas pelo líder;
- somente impressões legais no formato e data informados.

Fluxo recomendado:

```powershell
$env:PYTHONPATH = "src"

python -m optcg_lab validate data/lab.db examples/meu_deck.txt Standard --date 2026-09-17
python -m optcg_lab analyze data/lab.db examples/meu_deck.txt
python -m optcg_lab recommend data/lab.db examples/meu_deck.txt Standard --date 2026-09-17
python -m optcg_lab context data/lab.db examples/meu_deck.txt Standard outputs/meu_contexto.md --date 2026-09-17 --opponent OP17-039
```

## Como pedir melhoria do deck

No Codex, uma frase basta:

> Melhore `examples/meu_deck.txt` para Standard EN. Quero mais consistência geral. Faça mudanças mínimas, entregue entradas e saídas, gere a lista final completa com 50 cartas, valide novamente e crie um plano de 20 partidas para comparar com a versão atual.

Para um matchup específico:

> Melhore `examples/meu_deck.txt` contra `OP17-039 Rocks.D.Xebec`. Preserve o núcleo do líder. Use dados de matchup somente quando a fonte e a amostra estiverem claras. Entregue lista OPTCGSim completa e legal.

Para explorar opções:

> Crie três melhorias para `examples/meu_deck.txt`: conservadora, anti-meta e experimental. Em cada versão, mostre entradas, saídas, métricas antes/depois, riscos e hipótese de teste. Não invente aumento de win rate.

O fluxo obrigatório do agente é:

1. validar lista original;
2. analisar curva, counter, traits, keywords e cartas mortas;
3. procurar candidatos no catálogo legal completo;
4. consultar uso e matchup quando houver dados;
5. explicar problemas concretos;
6. propor trocas com entradas e saídas equivalentes;
7. gerar deck final completo;
8. validar versão proposta;
9. comparar métricas;
10. criar plano de testes.

Você pode acrescentar restrições:

- cartas que já possui;
- orçamento;
- estilo agressivo, controle ou midrange;
- preferência por ir primeiro ou segundo;
- decks mais comuns na loja;
- cartas que deseja manter;
- quantidade máxima de mudanças.

Sem essas informações, o agente usa consistência geral, catálogo completo e mudanças mínimas como padrão. Preço e disponibilidade física ficam marcados como não avaliados.

Um modelo reutilizável está em [`prompts/improve_deck.md`](prompts/improve_deck.md).

## Como usar com ChatGPT ou NotebookLM

ChatGPT e NotebookLM normalmente não executam o banco SQLite local. Gere um pacote Markdown:

```powershell
python -m optcg_lab context data/lab.db examples/meu_deck.txt Standard outputs/meu_contexto.md --date 2026-09-17 --opponent OP17-039
```

Envie `outputs/meu_contexto.md` à IA. O arquivo contém:

- líder, cores, vida, poder, traits e efeito;
- deck completo e efeitos relevantes;
- resultado da validação;
- métricas objetivas;
- candidatos fora da lista;
- evidência disponível de matchup;
- instruções para não inventar estatísticas ou legalidade.

Para NotebookLM, também podem ser enviados:

- `docs/SPECIFICATION.md`;
- `docs/DATA_SOURCES.md`;
- `docs/COMPLETION_AUDIT.md`;
- contextos de decks em `outputs/`.

Codex continua sendo a melhor opção para análise dinâmica, pois consegue executar consultas e validar listas novas.

## Como compartilhar com outra pessoa

### Pelo GitHub

1. Abra as configurações do repositório privado.
2. Entre em **Collaborators**.
3. Convide o usuário do seu amigo.
4. Ele aceita o convite e executa:

```powershell
git clone https://github.com/P3robr/one-piece-tcg-lab.git
cd one-piece-tcg-lab
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m optcg_lab status data/lab.db
```

### Por arquivo ZIP

Compacte a pasta inteira e envie. Cada pessoa deve trabalhar em uma cópia própria.

Não use o mesmo `data/lab.db` simultaneamente numa pasta sincronizada. `record-match` altera o banco; Dropbox, OneDrive ou Google Drive podem produzir conflitos.

## Comandos disponíveis

Todos os exemplos abaixo assumem:

```powershell
$env:PYTHONPATH = "src"
```

### Estado do banco

```powershell
python -m optcg_lab status data/lab.db
```

### Validar deck

```powershell
python -m optcg_lab validate data/lab.db examples/meu_deck.txt Standard --date 2026-09-17
```

Retorno `0` indica deck válido; retorno `1` indica erro de legalidade.

### Analisar deck

```powershell
python -m optcg_lab analyze data/lab.db examples/meu_deck.txt
```

### Recomendar candidatos

```powershell
python -m optcg_lab recommend data/lab.db examples/meu_deck.txt Standard --date 2026-09-17 --limit 20
```

### Consultar cartas

```powershell
python -m optcg_lab search data/lab.db --color Red --trait "Whitebeard Pirates" --keyword Blocker --block 2 --block 3 --block 4 --block 5 --block X
python -m optcg_lab search data/lab.db --color Red --text "Edward.Newgate" --max-cost 6
python -m optcg_lab search data/lab.db --category Character --min-counter 2000
```

### Consultar meta

```powershell
python -m optcg_lab meta data/lab.db Standard --environment simulator_global_op17
```

O ranking do snapshot descreve a variante representativa mostrada pela fonte, não participação total de cada líder.

### Consultar matchup

```powershell
python -m optcg_lab matchup data/lab.db OP14-020 OP17-039
```

### Registrar partida pessoal

```powershell
python -m optcg_lab record-match data/lab.db 2026-09-17 OP17-001 OP17-039 loss --second --deck-label newgate-v1 --notes "Faltou resposta ao turno 6"
```

Use `--first` ou `--second` quando conhecido. Omita ambos quando não souber.

### Gerar contexto para IA

```powershell
python -m optcg_lab context data/lab.db examples/meu_deck.txt Standard outputs/meu_contexto.md --date 2026-09-17 --opponent OP17-039
```

### Inicializar banco vazio

```powershell
python -m optcg_lab init-db data/novo.db
```

### Importar dataset JSON

```powershell
python -m optcg_lab import-json data/lab.db data/rules_en_2026.json
python -m optcg_lab import-json data/lab.db data/meta_op17_2026-09-17.json
```

### Atualizar catálogo oficial

```powershell
python -m optcg_lab sync-official data/lab.db
python -m optcg_lab reindex-keywords data/lab.db
```

### Atualizar uso de cartas do Newgate

```powershell
python -m optcg_lab sync-usage data/lab.db https://onepiecedecklists.com/decklists/op17/edward-newgate.html OP17-001 Standard --date 2026-09-17
```

O importador aceita somente listas válidas para o formato solicitado. Listas Extra ou antigas não contaminam a amostra Standard.

## Estrutura do projeto

```text
one-piece-tcg-lab/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── data/
│   ├── lab.db
│   ├── rules_en_2026.json
│   ├── meta_newgate_2026-09-14.json
│   └── meta_op17_2026-09-17.json
├── docs/
│   ├── COMPLETION_AUDIT.md
│   ├── DATA_SOURCES.md
│   └── SPECIFICATION.md
├── examples/
│   └── newgate_consensus_op17.txt
├── outputs/
│   ├── newgate_context.md
│   └── newgate_vs_rocks_context.md
├── src/optcg_lab/
│   ├── __init__.py
│   ├── __main__.py
│   ├── community.py
│   ├── lab.py
│   └── official.py
└── tests/
    └── test_lab.py
```

### Componentes

- `lab.py`: esquema SQLite, importação, validação, análise, busca, recomendações, meta, matchups e contexto.
- `official.py`: leitura das páginas públicas do catálogo oficial.
- `community.py`: leitura de listas públicas no formato usado pela fonte inicial.
- `__main__.py`: interface de linha de comando.
- `AGENTS.md`: protocolo para agentes de IA.

## Dados incluídos

### Catálogo

Snapshot do catálogo inglês oficial da Bandai, capturado em 14/09/2026:

- 2.785 números de carta;
- 4.843 impressões;
- 1.039 fatos de keyword;
- 142 líderes;
- 119 cartas OP17.

### Regras

- Standard EN: Blocks 2, 3, 4, 5 e X.
- Extra: Blocks 1, 2, 3, 4, 5 e X.
- 5 cartas banidas no snapshot.
- 3 pares proibidos.

### Meta

- 8 variantes representativas de simulador, capturadas em 17/09/2026.
- 15 matchups de torneio OP17, atualizados em 16/09/2026.
- 6 matchups adicionais de simulador envolvendo Edward.Newgate.
- 664 linhas de estatística de uso, cobrindo dois snapshots de 332 candidatos legais do Newgate.

### Caso inicial: Edward.Newgate OP17

- Consenso derivado de 17 listas públicas.
- 12 listas aceitas como Standard.
- 5 listas rejeitadas automaticamente por cartas de Block 1.
- Exemplo final possui 1 líder, 50 cartas e legalidade confirmada.

Consulte [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md) para proveniência e limites.

## Como interpretar resultados

### Recomendações

O score é triagem, não prova de força. Considera:

- compatibilidade de cor e formato;
- traits compartilhados;
- menções ao líder ou aos traits no efeito;
- funções como Blocker, Rush ou Trigger;
- frequência em amostras importadas, quando disponível.

Uma carta recebe a justificativa **“pouco usada”** somente quando existe amostra. Ausência de dados não é evidência de desuso.

### Matchups

Cada resultado preserva:

- fonte;
- data;
- ambiente;
- formato declarado;
- partidas;
- vitórias;
- intervalo Wilson de 95%;
- observações sobre vieses conhecidos.

Simulador, torneio presencial e partidas pessoais permanecem separados. O agregado só deve ser usado quando ambiente, período e formato forem comparáveis.

### Hipóteses de mudança

Ao testar uma carta:

1. declare entrada e saída;
2. mantenha legalidade e 50 cartas;
3. registre função pretendida;
4. escolha matchup-alvo;
5. teste versões A/B;
6. registre partidas comparáveis;
7. não transforme sequência curta de vitórias em conclusão definitiva.

## Atualização dos dados

O banco é um snapshot, não serviço em tempo real.

Antes de decisão competitiva importante:

1. atualize catálogo oficial;
2. revise regras e restrições oficiais;
3. importe novo snapshot de meta;
4. atualize uso do líder analisado;
5. execute testes;
6. valide novamente o deck.

```powershell
python -m optcg_lab sync-official data/lab.db
python -m optcg_lab import-json data/lab.db data/rules_en_2026.json
python -m optcg_lab reindex-keywords data/lab.db
python -m unittest discover -s tests -v
```

Regras e meta exigem revisão humana porque datas efetivas, metodologia e formatos podem mudar. Preserve snapshots antigos; não reescreva períodos históricos silenciosamente.

## Testes

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Cobertura atual:

- parsing de decklists e soma de linhas duplicadas;
- deck válido;
- erros de cor, restrição e par proibido;
- curva e counter;
- busca e recomendação;
- contexto e matchup;
- parsing do catálogo oficial;
- distinção entre keyword intrínseca e concedida;
- partida pessoal e status;
- parsing de listas comunitárias;
- relatório de meta.

## Limitações

- Efeitos são armazenados e parcialmente classificados, mas não existe simulador completo de regras.
- Líderes com construção especial exigem exceção codificada antes de validação automática.
- O sistema produz candidatos e hipóteses; não descobre matematicamente o “melhor deck”.
- A matriz atual de torneios mistura Standard e Extra porque a fonte não informa a regulação por evento.
- Habilidade do piloto, drop, ordem de turno e variante exata nem sempre estão disponíveis.
- A evidência detalhada de baixa utilização foi coletada inicialmente para Newgate. Outros líderes precisam de amostra própria antes de uma carta ser chamada de esquecida.
- `OP15-096` possui Block ausente na página oficial. Permanece `?` e não é presumida legal.
- Interface web, API hospedada, embeddings, Graphify e machine learning não fazem parte do núcleo atual.

## Direitos e uso dos dados

Este é um projeto independente, não oficial, sem afiliação ou endosso da Bandai, Shueisha, Toei Animation ou demais titulares de ONE PIECE.

Código, estrutura do banco e documentação são separados dos direitos sobre cartas, nomes, regras, textos e demais dados de terceiros. O snapshot foi preparado para pesquisa pessoal local. Não publique, redistribua ou comercialize o banco sem verificar permissões aplicáveis.

O projeto não baixa imagens das cartas.

Não há arquivo de licença neste repositório. Ausência de licença significa que nenhum direito amplo de reutilização do código é concedido automaticamente.

## Solução de problemas

### `No module named optcg_lab`

Defina `PYTHONPATH` na mesma sessão do terminal:

```powershell
$env:PYTHONPATH = "src"
```

Ou instale localmente:

```powershell
python -m pip install -e .
```

### `python` não encontrado

Instale Python 3.11 ou superior e habilite a opção de adicionar Python ao `PATH`. No Windows, tente:

```powershell
py -3.11 -m optcg_lab status data/lab.db
```

### Deck mostra quantidade incorreta

Confira se todas as linhas usam quantidade e número canônico:

```text
4xOP17-002
```

Linhas repetidas são somadas de propósito.

### Carta aparece ilegal apesar de possuir reprint

O validador considera todas as impressões conhecidas. Atualize o catálogo. Se continuar, consulte os Block Icons registrados e verifique se a fonte oficial informa o reprint.

### Resultado de matchup parece contraditório

Confira `environment`, `captured_at`, `format_name` e `games`. Fontes de simulador e torneio medem populações diferentes.

### Banco travado ou com arquivo `-wal`

Feche processos usando o banco. Não sincronize a mesma cópia entre dois computadores enquanto houver escrita.

## Documentação adicional

- [`docs/SPECIFICATION.md`](docs/SPECIFICATION.md): decisões, arquitetura e roadmap.
- [`docs/DATA_SOURCES.md`](docs/DATA_SOURCES.md): fontes, metodologia e governança.
- [`docs/COMPLETION_AUDIT.md`](docs/COMPLETION_AUDIT.md): cobertura dos requisitos e verificações.

---

Feito para análise crítica de deckbuilding: popularidade informa, mas não substitui legalidade, função, matchup e teste.
