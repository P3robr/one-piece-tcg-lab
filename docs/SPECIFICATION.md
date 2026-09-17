# Especificação do One Piece TCG Lab

Status: núcleo operacional auditado em 17/09/2026; evoluções avançadas permanecem condicionais.

## 1. Problema

Deckbuilding competitivo tende a convergir para listas já publicadas. Isso facilita entrada no jogo, mas cria três limitações:

1. cartas antigas ou pouco usadas deixam de ser consideradas;
2. popularidade passa a ser confundida com adequação ao matchup;
3. recomendações raramente explicam impacto sobre consistência, curva e defesa.

O One Piece TCG Lab deve ajudar o jogador a construir, comparar e testar decks com evidência. O sistema deve encontrar opções fora do consenso sem premiar novidade por si só.

## 2. Objetivo

Responder perguntas como:

- Este deck é legal no formato e data informados?
- Quais são os principais problemas desta lista?
- Quais cartas legais cumprem uma função ausente?
- Quais cartas pouco usadas combinam com este líder?
- Como este líder se comporta contra outro líder?
- Como o plano muda indo primeiro ou segundo?
- Quais trocas melhoram um matchup sem prejudicar demais os demais?
- O que mudou entre duas versões do deck?
- O que aprendemos com minhas partidas?

## 3. Não objetivos do MVP

- Treinar uma LLM própria.
- Prever com certeza o resultado de uma partida.
- Encontrar matematicamente o melhor deck entre todas as combinações.
- Misturar resultados de simulador e torneio num win rate único.
- Reproduzir ou publicar imagens e textos protegidos sem autorização.
- Criar rede social, marketplace ou simulador de partidas.
- Usar Graphify antes de existir um corpus estável.

## 4. Usuário inicial

O primeiro usuário é o proprietário do projeto. A experiência será otimizada para uso pessoal dentro do Codex. Suporte a outros usuários, publicação web e uso pelo ChatGPT comum serão decisões posteriores.

## 5. Caso vertical inicial

Líder: Edward.Newgate `OP17-001`.

O primeiro fluxo completo deverá:

1. carregar o líder e sua lista;
2. determinar formato e data de análise;
3. validar cores, quantidade, cópias e restrições;
4. identificar núcleo, motor, defesa, pressão, controle, finalizadores e flex slots;
5. medir curva, counter, bricks e cobertura de traits;
6. recuperar cartas vermelhas legais e sinergias relevantes;
7. comparar uso competitivo e alternativas pouco usadas;
8. produzir três propostas: consolidada, anti-meta e experimental;
9. explicar trocas, riscos e confiança;
10. registrar resultados de testes posteriores.

## 6. Arquitetura conceitual

### 6.1 Fonte de verdade

SQLite será a fonte de verdade inicial. JSON e Markdown serão exportações, não armazenamento canônico.

Motivos:

- consulta exata por cor, trait, custo e formato;
- validação de integridade;
- atualização incremental;
- portabilidade em um único arquivo;
- nenhuma infraestrutura de servidor no MVP.

### 6.2 Motor determinístico

Responsável por:

- legalidade;
- parsing de decklists;
- contagens;
- curva;
- counter total e distribuição;
- probabilidades hipergeométricas;
- número de alvos de searchers;
- detecção de cartas potencialmente mortas;
- comparação objetiva entre versões.

### 6.3 Recuperação de candidatos

Antes de consultar a LLM, o sistema reduz o catálogo usando:

- formato e data;
- cores do líder;
- restrições específicas;
- traits;
- palavras-chave;
- funções mecânicas;
- custo e curva;
- compatibilidade com searchers;
- necessidades do matchup.

A LLM recebe candidatos relevantes, não o catálogo inteiro.

### 6.4 Camada LLM

Responsável por:

- interpretar plano de jogo;
- explicar relações entre efeitos;
- formular hipóteses;
- propor pacotes de cartas;
- comparar trade-offs;
- produzir planos de matchup e mulligan.

Toda afirmação factual deve apontar para dados recuperados. Toda recomendação deve ser marcada como hipótese até ser testada.

## 7. Modelo de dados

### 7.1 Card

- número canônico;
- nome;
- categoria: Leader, Character, Event ou Stage;
- cores;
- custo;
- poder;
- vida;
- counter numérico;
- atributo;
- raridade;
- Block Icon;
- texto oficial;
- idioma;
- conjunto de origem;
- fonte;
- data de captura;
- hash do conteúdo.

Artes alternativas e reprints serão registros de impressão separados da identidade de jogo.

### 7.2 Trait

Traits serão relação muitos-para-muitos. Texto original será preservado. Normalização não poderá apagar diferenças entre nomes semelhantes.

### 7.3 EffectFact

Um booleano `is_blocker` ou `is_rush` não representa todos os casos. Cada fato de efeito poderá conter:

- mecânica;
- sujeito;
- alvo;
- timing;
- condição;
- custo adicional;
- duração;
- zona de origem;
- zona de destino;
- valor numérico;
- trecho de evidência;
- método de extração;
- confiança;
- versão do parser;
- revisão manual.

O texto oficial continua sendo autoridade.

### 7.4 Format e LegalitySnapshot

- nome do formato;
- região;
- início de vigência;
- fim de vigência;
- Block Icons permitidos;
- cards banidos;
- cards restritos;
- pares proibidos;
- exceções;
- fonte oficial.

Legalidade sempre será consultada para uma data. Estado atual não será sobrescrito sem manter histórico.

### 7.5 Deck e DeckVersion

- líder;
- formato;
- lista de cards e quantidades;
- origem;
- autor;
- data;
- versão pai;
- observações;
- tags de finalidade.

### 7.6 Event, Entrant e Match

Event:

- nome, data, região, tamanho, formato, plataforma e fonte.

Entrant:

- jogador anonimizado quando necessário, líder, decklist, colocação e recorde.

Match:

- rodada, jogadores, líderes, vencedor, primeiro jogador quando disponível e resultado.

Ausência de campo será `unknown`, nunca inferência silenciosa.

### 7.7 PersonalMatch

- data;
- versão do deck;
- líder adversário;
- primeiro ou segundo;
- resultado;
- mulligan;
- cartas boas;
- cartas mortas;
- observações;
- ambiente.

Dados pessoais não serão misturados com meta global.

## 8. Proveniência dos dados

Cada dado terá fonte, captura e método de obtenção. Hierarquia:

1. site oficial para cartas, regras, erratas e restrições;
2. partidas por rodada de torneios para matchups presenciais;
3. simuladores para volume e recortes primeiro/segundo;
4. top cuts para padrões de construção;
5. artigos e comunidade para hipóteses estratégicas.

Uma fonte não será usada para responder pergunta que ela não mede. Top cuts ajudam a entender listas bem-sucedidas, mas não produzem win rate confiável sozinhos.

## 9. Estatística de matchup

Resultados serão separados por:

- set;
- formato;
- região;
- período;
- simulador ou presencial;
- primeiro ou segundo;
- variante do arquétipo quando identificável.

Toda taxa mostrará número de partidas. Amostras pequenas terão redução em direção a uma média conservadora e intervalo de incerteza. Mirrors serão tratados separadamente.

O sistema deverá declarar vieses conhecidos:

- seleção de jogadores;
- habilidade não observada;
- desistências em torneios suíços;
- listas ausentes;
- formato desconhecido;
- duplicação entre agregadores;
- diferença entre simulador e papel;
- mudança do meta ao longo do tempo.

## 10. Análise de deck

### 10.1 Papéis

Cards poderão cumprir vários papéis:

- núcleo do líder;
- searcher;
- alvo de search;
- geração de mão;
- 1000 ou 2000 counter;
- blocker;
- pressão imediata;
- remoção;
- proteção;
- recuperação;
- ramp ou manipulação de DON!!;
- manipulação de vida;
- finalizador;
- tech de matchup;
- brick contextual.

Papéis condicionais devem conservar condição.

### 10.2 Métricas mínimas

- quantidade total;
- distribuição por categoria;
- curva por custo impresso e custo efetivo conhecido;
- cards sem counter;
- soma e distribuição de counter;
- blockers diretos e condicionais;
- Rush direto, condicional e concedido;
- densidade de cada trait;
- alvos por searcher;
- cards não pesquisáveis;
- redundância funcional;
- quantidade de finalizadores;
- dependências entre cards.

### 10.3 Candidatos esquecidos

Uma carta pouco usada só será recomendada quando houver função concreta. Avaliação:

- legalidade;
- sinergia com líder;
- sinergia por trait;
- possibilidade de busca;
- adequação à curva;
- valor defensivo;
- valor no matchup;
- custo de oportunidade;
- popularidade recente;
- evidência favorável e contrária;
- motivo provável do desuso.

Novidade não será tratada como qualidade.

## 11. Contrato de resposta

Análise de deck deverá conter:

1. validade e avisos;
2. resumo do plano atual;
3. métricas principais;
4. fragilidades;
5. candidatos encontrados;
6. trocas propostas;
7. impacto estimado das trocas;
8. riscos;
9. evidências e amostras;
10. plano de teste.

Análise de matchup deverá conter:

1. taxa observada por fonte;
2. amostra, período e incerteza;
3. diferença primeiro/segundo quando disponível;
4. explicação estratégica;
5. mulligan e prioridades;
6. cards relevantes;
7. adaptações sugeridas;
8. confiança e dados ausentes.

Nenhum win rate futuro será inventado para uma troca não testada.

## 12. Modos de recomendação

### Consolidado

Mantém núcleo comprovado. Poucas alterações. Prioriza consistência.

### Anti-meta

Otimiza contra distribuição de adversários informada. Aceita perdas controladas em matchups menos relevantes.

### Experimental

Testa cartas pouco usadas com justificativa. Mudanças serão isoladas para permitir avaliação.

## 13. Avaliação

Uma recomendação será considerada útil quando:

- for legal;
- citar card correto;
- explicar função e condição;
- indicar entrada e saída;
- preservar ou quantificar mudanças de consistência;
- declarar risco;
- possuir teste verificável;
- não usar popularidade como única justificativa.

Conjunto inicial de avaliações:

- decks válidos e inválidos conhecidos;
- efeitos diretos e condicionais;
- líderes mono e multicoloridos;
- cards banidos e pares proibidos;
- searchers com alvos insuficientes;
- comparação antes e depois;
- matchups com amostra pequena e grande;
- decks propositalmente cheios de cards populares, mas incoerentes.

## 14. Roadmap

Estado em 17/09/2026: os Marcos 1 a 4 estão operacionais no escopo local. Há catálogo completo até OP17, validação por data, uso por carta, snapshot do meta, matchups por fonte, diário pessoal e exportação Markdown. Interface, API e aprendizado continuam deliberadamente opcionais.

### Marco 1: fundação local

- esquema SQLite;
- importação de JSON ou CSV;
- parser de lista OPTCGSim;
- validador;
- métricas básicas;
- testes pequenos e reproduzíveis.

### Marco 2: Edward.Newgate OP17

- catálogo vermelho Standard;
- traits e efeitos relevantes;
- listas recentes;
- análise consolidada, anti-meta e experimental;
- exportação de contexto para ChatGPT.

### Marco 3: meta

- importação versionada de eventos, jogadores e partidas;
- matriz de matchups;
- separação de fontes;
- recência, amostra e incerteza.

### Marco 4: experiência conversacional

- comandos de consulta para o Codex;
- respostas com proveniência;
- comparação de versões;
- diário pessoal.

### Marco 5: acesso externo opcional

- API pequena ou GPT Action;
- uso pelo ChatGPT fora do Codex;
- autenticação somente se houver dados privados ou múltiplos usuários.

### Marco 6: aprendizado opcional

Somente após existir histórico suficiente e objetivo mensurável. Primeira opção será modelo estatístico de ranking ou matchup. Fine-tuning de LLM continua fora até haver muitos exemplos avaliados.

## 15. Decisões adiadas

- interface web;
- hospedagem;
- embeddings;
- banco vetorial;
- Graphify;
- machine learning;
- suporte público;
- imagens das cartas;
- monetização.

Essas decisões serão retomadas apenas quando o MVP demonstrar necessidade.

## 16. Próximas evoluções condicionais

- Automatizar novos snapshots de meta apenas com uma fonte estável e uso permitido.
- Codificar exceções de líderes com regra especial quando um caso real exigir.
- Adicionar interface ou API somente se o fluxo por Codex/Markdown se mostrar insuficiente.
- Considerar ranking estatístico depois de acumular versões de deck e partidas pessoais comparáveis.
