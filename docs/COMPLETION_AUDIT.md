# Auditoria de conclusão

Data: 17/09/2026.

## Resultado

O núcleo local do One Piece TCG Lab está funcional e cobre o objetivo original: fornecer fatos estruturados, regras, evidência de meta e recuperação de cartas pouco usadas para uma IA discutir, validar e melhorar decks. Não foi treinado um modelo próprio; isso não acrescentaria valor nesta fase e exigiria um conjunto de exemplos rotulados que ainda não existe.

## Cobertura dos requisitos

| Requisito | Implementação e evidência |
|---|---|
| Todas as cartas disponíveis até OP17 | `data/lab.db`: 2.785 números e 4.843 impressões; 119 cartas OP17. |
| Nome, tipo, cor, custo, poder, vida, counter, traits/famílias e efeito | Tabelas normalizadas de cards, cores, traits, impressões e texto oficial. Líderes preservam vida individual. |
| Rush, Blocker, Trigger e outras keywords | 1.039 fatos extraídos com distinção entre keyword intrínseca e apenas concedida/mencionada; Trigger também preserva o texto próprio. |
| Regras de construção | Validação de 1 líder, 50 cartas principais, até 4 cópias, compatibilidade de cores, Block por data, banimentos, restrições e pares proibidos. |
| Rotação atual | Standard EN vigente desde 10/04/2026 com Blocks 2, 3, 4, 5 e X; Extra preservado separadamente. |
| Meta atual | 8 variantes representativas do simulador capturadas em 17/09/2026 e 15 confrontos de torneio atualizados em 16/09/2026. |
| Matchup contra matchup | Relatório por fonte, ambiente, data, amostra, taxa bruta e intervalo Wilson de 95%; partidas pessoais ficam separadas. |
| Não depender só de top decks | Busca considera todo o catálogo legal. A amostra de uso inclui também cartas com zero aparições, permitindo provar baixa utilização. |
| Tratar listas antes de confiar nelas | Das 17 listas públicas de Newgate, 12 foram aceitas como Standard e 5 rejeitadas por Block 1. |
| Encontrar cartas antigas esquecidas | Ranking combina legalidade, traits, texto, função e baixa presença. “Pouco usada” só aparece quando existe amostra. |
| Conversar com IA | Comando `context` gera Markdown autocontido com líder, deck, validação, métricas, candidatos, efeitos e matchup. |
| Uso contínuo | Comandos para atualizar catálogo/uso, importar snapshots, registrar partidas e consultar estado. `AGENTS.md` define o protocolo da IA. |

## Verificações executadas

- 10 testes automatizados passaram.
- A lista `examples/newgate_consensus_op17.txt` passou no Standard em 17/09/2026 sem erros ou avisos.
- `OP17-001` foi conferido como líder vermelho, vida 5 e poder 5000.
- A matriz Mihawk `OP14-020` versus Rocks `OP17-039` retornou 130–56 em 186 partidas de torneio.
- A busca de candidatos do Newgate encontrou cartas legais com 0% ou 8,3% de presença em 12 listas válidas.
- Não há cartas sem cor nem identificadores de impressão duplicados.

## Limites deliberados

- Efeitos são pesquisáveis e parcialmente classificados, mas o sistema não simula a resolução completa de uma partida.
- A matriz presencial atual mistura Standard e Extra porque a fonte não informa a regulação; o banco declara essa incerteza.
- Estatística sugere hipótese, não causalidade. Mudanças de lista devem ser testadas em partidas comparáveis.
- A impressão oficial de `OP15-096` não informa Block; ela permanece `?` e não é presumida legal.
- Líderes com exceção especial de construção exigem regra explícita antes da validação automática.
- Interface web, Graphify, embeddings e machine learning continuam fora do núcleo porque não são necessários para o fluxo local atual.

## Critério de atualização

Antes de uma decisão competitiva importante, atualize catálogo, regras, uso e meta; depois execute novamente testes, validação do deck e relatório do matchup. Snapshots antigos devem ser preservados para evitar reescrever a história.
