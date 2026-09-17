# Fontes e governança de dados

## Hierarquia

1. Bandai em inglês: texto de carta, número, categoria, cor, custo/vida, poder, counter, Block, atributos, tipos, efeitos, triggers, regras e restrições.
2. Torneios com rodadas e listas: desempenho competitivo e matchups presenciais.
3. Simuladores: amostras maiores, identificadas como ambiente digital.
4. Sites de listas: composição e frequência; resultado isolado não prova que uma carta é boa.
5. Partidas pessoais: evidência do piloto, sempre separada.

## Snapshot incluído

- Catálogo: `https://en.onepiece-cardgame.com/cardlist/`, capturado em 14/09/2026.
- Formato: carta da equipe de desenvolvimento de 09/01/2026; Standard permite Block 2 ou superior e Block X é tratado como permanente pela implementação.
- Restrições: página oficial vigente desde 10/04/2026; cinco banimentos, nenhum card restrito e três pares proibidos.
- Deck inicial: consenso de 17 listas OP17 publicado por One Piece Decklists, capturado em 14/09/2026.
- Matchups do Newgate: Straw Hat Stats, ambiente de simulador, capturado em 14/09/2026.
- Uso de cartas do Newgate: One Piece Decklists, recapturado em 17/09/2026; 12 das 17 listas passaram na validação Standard.
- Meta de variantes representativas: Straw Hat Stats, capturado em 17/09/2026. A posição é da variante mais jogada exibida para cada líder, não participação total do líder.
- Matriz OP17: Corazón TCG com rodadas do Limitless, atualizada em 16/09/2026; 3.083 partidas de 23 torneios nos últimos 35 dias. A fonte não permite separar Standard de Extra, portanto o banco marca `tournament_rounds_mixed_regulation`.

A auditoria encontrou uma impressão com Block ausente na própria página oficial (`OP15-096`). Ela permanece `?` e não é presumida legal pelo sistema até a fonte ser corrigida ou uma exceção documentada ser adicionada.

## Atualização

Cartas são atualizadas por `sync-official`. Regras permanecem versionadas em JSON porque datas efetivas e exceções exigem revisão humana. Meta deve entrar em novos snapshots; não sobrescreva silenciosamente um período antigo.

Cada estatística precisa ter fonte, URL, data, formato, ambiente, líderes, partidas e vitórias. Quando disponíveis, registre ordem de turno, versão da lista e notas sobre filtros.

## Limites legais e operacionais

A Bandai declara que imagens, textos e dados não podem ser reproduzidos sem permissão. O Lab não baixa imagens e destina o snapshot a pesquisa pessoal local. Não publique nem redistribua o banco sem verificar permissões aplicáveis. O código do Lab é separado dos direitos sobre os dados das cartas.

Sites comunitários podem mudar, remover páginas ou impor limites. O banco local e hashes de captura tornam análises reproduzíveis, mas não concedem direitos sobre o conteúdo de terceiros.
