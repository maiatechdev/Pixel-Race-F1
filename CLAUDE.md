# CLAUDE.md — Distributed Racing

## 1. Visão geral

**Distributed Racing** é um projeto acadêmico da disciplina de **Sistemas Distribuídos**.

O jogo será uma corrida arcade em **pixel art**, inspirada visualmente em automobilismo/Fórmula 1, para **exatamente 2 jogadores**. A mecânica central é propositalmente simples: os jogadores alternam turnos e solicitam ao servidor o lançamento de um dado. O resultado determina o avanço do carro na corrida.

A simplicidade da regra é intencional. O objetivo acadêmico principal não é criar um simulador complexo, e sim demonstrar corretamente:

- arquitetura cliente-servidor;
- comunicação remota via RPC;
- múltiplos clientes;
- estado compartilhado;
- concorrência;
- sincronização;
- validação de ações no servidor;
- consistência do estado;
- tratamento de desconexões/falhas básicas.

A experiência visual, porém, deve parecer um pequeno jogo de corrida arcade completo.

---

## 2. Stack definida

### Backend
- Python
- gRPC
- Protocol Buffers (`.proto`)
- Estado mantido inicialmente em memória
- Concorrência/sincronização explícita no servidor

### Cliente / frontend
- Python
- Pygame
- Assets PNG em pixel art
- Áudio opcional

### Não usar inicialmente
- Flask
- FastAPI
- Django
- API REST
- banco de dados
- autenticação
- contas de usuário
- microserviços
- serviços externos

Não adicionar frameworks ou dependências sem necessidade real.

---

## 3. Uso de IA no projeto

IA pode ser utilizada livremente como ferramenta de apoio ao desenvolvimento do projeto, tanto no frontend quanto no backend.

Claude pode:

- implementar e refatorar código Pygame;
- implementar telas, animações, HUD e efeitos;
- organizar e integrar assets;
- auxiliar na definição e implementação do contrato gRPC;
- implementar e revisar o cliente e o servidor gRPC;
- auxiliar na lógica autoritativa da partida;
- implementar e revisar mecanismos de concorrência e sincronização;
- criar testes;
- identificar e corrigir race conditions;
- auxiliar na arquitetura do projeto;
- escrever e revisar documentação;
- explicar as decisões técnicas tomadas.

Mesmo utilizando IA, priorizar código simples, compreensível e que possa ser explicado pelos integrantes do grupo.

# 4. Conceito do jogo

O jogo terá dois jogadores:

- Player 1 — carro vermelho;
- Player 2 — carro azul.

Visualmente, ambos aparecem simultaneamente em uma pista lateral.

A corrida possui uma distância lógica discreta. Inicialmente:

```text
START                                      FINISH
0 --------------------------------------------- 30
```

Cada jogador possui uma posição:

```text
Player 1 = 12
Player 2 = 9
```

No seu turno, o jogador pressiona o botão de jogar o dado.

O cliente **NÃO gera o dado**.

Fluxo conceitual:

```text
CLIENTE
   |
   | RollDice
   v
SERVIDOR
   |
   | valida jogador
   | valida turno
   | gera número 1..6
   | atualiza posição
   | verifica vitória
   | altera turno
   v
NOVO ESTADO
   |
   v
CLIENTES
```

O servidor é sempre a **fonte autoritativa da verdade**.

---

# 5. Regras do MVP

Começar pequeno.

## Partida

- exatamente 2 jogadores;
- uma corrida ativa inicialmente;
- pista lógica com 30 unidades;
- ambos começam na posição 0;
- dado de 1 a 6;
- jogadores alternam turnos;
- resultado do dado é produzido pelo servidor;
- jogador avança o valor sorteado;
- posição >= 30 significa vitória;
- após vitória, nenhuma nova jogada deve alterar a partida;
- estado permanece no servidor.

Exemplo:

```text
Gabriel
posição = 13

dado = 5

nova posição = 18
```

Depois:

```text
turnoAtual = Player 2
```

---

# 6. O servidor é autoritativo

O cliente nunca deve enviar:

```text
"eu tirei 6"
```

nem:

```text
"minha nova posição é 24"
```

O cliente solicita apenas uma ação:

```text
"quero jogar o dado"
```

O servidor decide:

- se o jogador existe;
- se a partida começou;
- se a partida terminou;
- se é o turno dele;
- qual foi o resultado do dado;
- qual é a nova posição;
- quem é o próximo jogador;
- se alguém venceu.

Isso impede clientes de manipularem diretamente o estado.

---

# 7. Concorrência

Este é um dos pontos acadêmicos centrais.

Considere:

```text
turnoAtual = Player 1
```

Duas requisições podem chegar quase simultaneamente:

```text
Thread A -> RollDice(Player 1)
Thread B -> RollDice(Player 1)
```

Sem sincronização, ambas poderiam validar o mesmo turno antes que o estado fosse alterado.

Resultado incorreto:

```text
Thread A -> dado 4
Thread B -> dado 6

Player 1 joga duas vezes
```

O backend deverá impedir isso por meio de sincronização apropriada.

Claude pode implementar, explicar e revisar a sincronização do servidor. A solução deve permanecer simples o bastante para que o grupo consiga explicá-la e defendê-la na avaliação.

---

# 8. Estado conceitual da partida

O servidor deverá possuir um estado equivalente a:

```text
GameState
|
|-- status
|     WAITING
|     RUNNING
|     FINISHED
|
|-- players
|     |-- Player 1
|     |     id
|     |     name
|     |     position
|     |
|     |-- Player 2
|           id
|           name
|           position
|
|-- current_turn
|
|-- winner
|
|-- turn_number
```

Não assumir que essa estrutura precisa ser implementada literalmente dessa maneira. Ela representa o modelo conceitual.

---

# 9. gRPC

A comunicação cliente-servidor utilizará **gRPC + Protocol Buffers**.

O arquivo `.proto` será o contrato entre os dois lados.

Operações conceituais previstas:

```text
JoinGame
GetGameState
RollDice
LeaveGame
```

Opcionalmente:

```text
StartGame
```

dependendo da decisão do grupo sobre início automático ou host.

Evitar criar dezenas de RPCs. O contrato deve permanecer pequeno e fácil de defender academicamente.

---

# 10. Atualização dos clientes

Na primeira versão, priorizar simplicidade.

É aceitável utilizar polling para consultar o estado:

```text
Client -> GetGameState()
```

em pequenos intervalos.

Uma evolução futura pode utilizar recursos de streaming do gRPC para transmitir atualizações.

Não implementar streaming antes do MVP funcionar.

---

# 11. Arquitetura

```text
                  PYTHON SERVER
                      gRPC
                        |
              +---------+---------+
              |                   |
              |                   |
            gRPC                 gRPC
              |                   |
              v                   v
       PYGAME CLIENT 1     PYGAME CLIENT 2
          carro vermelho      carro azul
```

Os clientes devem conseguir rodar em computadores diferentes conectados pela rede.

---

# 12. Separação de responsabilidades

## Backend

Responsável por:

- jogadores;
- estado da partida;
- turnos;
- dado;
- posições;
- vitória;
- validação;
- concorrência;
- consistência;
- comunicação gRPC.

## Frontend

Responsável por:

- renderização;
- animações;
- input;
- HUD;
- sons;
- sprites;
- interpolação visual;
- efeitos;
- telas;
- feedback ao jogador.

Regra fundamental:

> **Pygame apresenta o estado. O servidor determina o estado.**

---

# 13. Direção visual

O jogo possui estética de corrida retrô em **pixel art 16/32-bit**.

Referência conceitual:

```text
+------------------------------------------------------+
| céu / nuvens / montanhas                             |
|                                                      |
| arquibancadas / árvores / torre                      |
|------------------------------------------------------|
| grade / barreiras                                    |
|------------------------------------------------------|
|                                                      |
|          CARRO VERMELHO                              |
|======================================================|
|                                                      |
|              CARRO AZUL                              |
|======================================================|
|                                                      |
+------------------------------------------------------+
| Player 1       DADO / TURNO        Player 2          |
| 18/30                               15/30             |
+------------------------------------------------------+
```

A câmera é predominantemente lateral.

Os dois carros precisam permanecer visíveis para que o jogador perceba imediatamente quem está na frente.

---

# 14. Movimento visual não é estado lógico

Não confundir posição lógica com coordenada de tela.

Servidor:

```text
Player 1:
position = 18
```

Frontend:

```text
logical_position -> visual_position
```

O Pygame pode interpolar e animar livremente.

Exemplo:

```text
posição lógica
12 -> 17
```

Visualmente:

1. dado mostra 5;
2. motor acelera;
3. rodas animam;
4. partículas aparecem;
5. cenário começa a se deslocar;
6. carro avança visualmente;
7. HUD atualiza;
8. animação desacelera;
9. carro chega à representação da posição 17.

A animação não pode alterar o estado autoritativo.

---

# 15. Parallax

O cenário será construído por camadas independentes.

Ordem aproximada:

```text
Layer 1 -> céu
Layer 2 -> nuvens / horizonte
Layer 3 -> montanhas
Layer 4 -> arquibancada
Layer 5 -> elementos intermediários quando necessários
Layer 6 -> árvores

trackside -> torre / postes / semáforo
barriers  -> grade / muro / pneus
ground    -> grama / zebra
track     -> asfalto
cars      -> jogadores
effects   -> fumaça / faíscas / chama
UI        -> HUD
```

Cada camada poderá se mover em velocidade diferente:

```text
céu             ~ 0
montanhas       lento
árvores         médio
arquibancada    médio
barreiras       rápido
asfalto         rápido
```

Isso cria profundidade sem exigir cenário 3D.

---

# 16. Assets

Estrutura atual (arquivos existentes):

```text
assets/
|
|-- cars/
|   |-- red/                  # Player 1
|   |   |-- idle.png
|   |   `-- accelerate.png
|   |
|   `-- blue/                 # Player 2
|       |-- idle.png
|       `-- accelerate.png
|
|-- wheels/
|   `-- wheel_sheet.png       # planilha de animação das rodas (compartilhada pelos dois carros)
|
|-- helmets/
|   |-- red.png
|   `-- blue.png
|
|-- background/
|   |-- sky.png
|   |-- mountains.png
|   |-- trees.png
|   |-- grandstand.png
|   `-- city_panorama.png     # cena completa já composta (alternativa às camadas)
|
|-- track/
|   |-- asphalt.png
|   |-- curb_red_white.png
|   |-- grass.png
|   `-- finish_line.png
|
|-- barriers/
|   |-- tire_wall.png
|   |-- concrete_wall.png
|   `-- fence.png
|
`-- circuit/
    |-- starting_lights.png   # pórtico de largada
    |-- lamp_post.png
    `-- control_tower.png
```

Pastas previstas, ainda **sem arquivos**: `effects/` (smoke, sparks, exhaust), `ui/` (dice, icons, flags, hud), `fonts/`, `audio/`.

**Atenção — os PNGs atuais não têm transparência real.** Todos estão em RGB, sem canal alfa, e o "xadrez" cinza e branco de fundo transparente está desenhado nos próprios pixels. Além disso, são imagens grandes (≈2172x724, carros 1983x793, elementos 1536x1024), não sprites em grade de pixel nativa. Antes de usar como camadas ou sprites, será preciso remover o fundo e reduzir para a escala de pixel art.

Antes de escrever código dependente de assets, **inspecione o diretório existente e use os nomes reais**.

Não invente caminhos para arquivos que ainda não existem.

---

# 17. Pixel art

Preservar pixels nítidos.

Evitar:

- blur;
- antialiasing visual nos sprites;
- filtros suaves ao ampliar;
- escalonamento que destrua a grade de pixels.

Preferir escalas inteiras sempre que possível:

```text
1x
2x
3x
4x
```

Para assets pequenos, utilizar técnicas equivalentes a nearest-neighbor.

---

# 18. Carros

Existem dois carros principais:

```text
Player 1 -> vermelho
Player 2 -> azul
```

Ambos devem seguir a mesma escala, perspectiva lateral e linguagem visual.

Estados previstos:

```text
IDLE
ACCELERATING
MOVING
FINISH
```

Não é obrigatório possuir sprites diferentes para todos os estados. Alguns efeitos podem ser compostos por:

- sprite base;
- roda animada;
- fumaça;
- chama;
- shake;
- deslocamento do cenário.

---

# 19. HUD

O HUD ainda será desenvolvido.

Informações mínimas:

```text
PLAYER 1
nome
posição
progresso

PLAYER 2
nome
posição
progresso

TURNO ATUAL

DADO

botão:
JOGAR DADO

status:
AGUARDANDO
SUA VEZ
VEZ DO ADVERSÁRIO
CORRIDA FINALIZADA
```

Possível composição:

```text
+------------------------------------------------+
| GABRIEL          [ DADO ]          LUCAS       |
| P1 18/30           5               P2 15/30    |
| ████████---                    ██████-----     |
|                                                |
|               [ JOGAR DADO ]                   |
|                  SUA VEZ                       |
+------------------------------------------------+
```

O HUD deve respeitar a estética pixel art.

---

# 20. Dado

O dado é a interação principal.

Fluxo visual desejado:

```text
click
  |
  v
animação do dado
  |
  v
aguarda/confirma resultado do servidor
  |
  v
resultado aparece
  |
  v
carro acelera
  |
  v
posição visual atualiza
```

Muito importante:

A animação pode mostrar faces aleatórias enquanto aguarda, mas o **resultado final deve ser exatamente o valor recebido do servidor**.

---

# 21. Largada

A corrida pode possuir uma sequência visual:

```text
READY

RED LIGHTS
● ● ● ● ●

...

GO!
```

Isso é apresentação.

O início real da partida deve depender do estado recebido do servidor.

---

# 22. Linha de chegada

Quando:

```text
position >= 30
```

o servidor determina o vencedor.

O frontend então executa a sequência visual:

```text
carro cruza a linha
bandeira quadriculada
efeitos
resultado
```

Tela final prevista:

```text
=========================
       RACE FINISHED
=========================

        PLAYER 1

          WINS

       [ resultado ]

      PLAY AGAIN?
=========================
```

`PLAY AGAIN` é opcional para versões posteriores.

---

# 23. Telas previstas

## 1. Menu

```text
DISTRIBUTED RACING

[ JOGAR ]
[ SAIR ]
```

## 2. Conexão

Permitir informar quando necessário:

```text
nome
IP/endereço do servidor
porta
```

## 3. Lobby

```text
PLAYER 1   READY
PLAYER 2   WAITING
```

## 4. Corrida

Tela principal.

## 5. Resultado

Vencedor e resumo.

---

# 24. Estrutura sugerida do projeto

Não tratar esta estrutura como imutável.

```text
distributed-racing/
|
|-- client/
|   |-- main.py
|   |
|   |-- screens/
|   |   |-- menu.py
|   |   |-- lobby.py
|   |   |-- race.py
|   |   `-- result.py
|   |
|   |-- components/
|   |   |-- car.py
|   |   |-- dice.py
|   |   |-- hud.py
|   |   `-- parallax.py
|   |
|   `-- grpc_client/
|       `-- ...
|
|-- server/
|   |-- server.py
|   |-- game.py
|   |-- player.py
|   `-- ...
|
|-- proto/
|   `-- racing.proto
|
|-- assets/
|
|-- requirements.txt
|
|-- README.md
|
`-- CLAUDE.md
```

Não reorganizar grandes partes do projeto sem necessidade.

---

# 25. Estados do frontend

Separar estado de rede de estado de animação.

Exemplo:

```text
Network/Game State:
player_position = 17
current_turn = PLAYER_2

Visual State:
car_x = 463.2
animation = ACCELERATING
smoke_timer = 0.14
```

Nunca modificar o estado remoto para facilitar uma animação.

---

# 26. Filosofia de desenvolvimento

Prioridade:

```text
FUNCIONA
   ↓
FUNCIONA EM DOIS CLIENTES
   ↓
ESTADO É CONSISTENTE
   ↓
ANIMAÇÃO
   ↓
POLIMENTO
```

Não inverter essa ordem.

---

# 27. Roadmap

## Fase 0 — Preparação

- criar estrutura do repositório;
- configurar ambiente Python;
- instalar Pygame;
- instalar ferramentas gRPC;
- organizar assets;
- definir resolução base;
- validar carregamento dos assets.

## Fase 1 — Protótipo visual offline

Sem backend.

Objetivo:

- abrir janela;
- renderizar pista;
- renderizar parallax;
- mostrar dois carros;
- mostrar HUD provisório;
- animar carro usando dados falsos locais.

Utilizar um mock semelhante a:

```text
player1.position = 10
player2.position = 7
dice = 4
turn = PLAYER_1
```

Isso é apenas frontend.

## Fase 2 — Contrato

Grupo define manualmente:

- mensagens;
- RPCs;
- parâmetros;
- retornos;
- erros;
- estados.

Depois define `racing.proto`.

## Fase 3 — Backend

Implementar e testar o backend gRPC da partida.

Objetivos:

- servidor;
- jogadores;
- partida;
- turnos;
- dado;
- estado;
- sincronização;
- validações.

## Fase 4 — Integração

Substituir mock do frontend por cliente gRPC real.

```text
mock
  ↓
gRPC adapter
  ↓
server
```

Idealmente a camada visual não deve precisar saber detalhes internos do RPC.

## Fase 5 — Multiplayer real

Testar:

```text
PC A -> cliente
PC B -> cliente
PC C ou A -> servidor
```

Verificar:

- conexão;
- turnos;
- concorrência;
- atualização;
- vitória;
- desconexão.

## Fase 6 — Polimento

- partículas;
- áudio;
- animação do dado;
- largada;
- linha de chegada;
- HUD final;
- menus;
- feedback de erro;
- transições.

---

# 28. MVP obrigatório antes de features extras

O MVP está pronto quando:

1. servidor inicia;
2. dois clientes conectam;
3. ambos aparecem na partida;
4. servidor inicia/autoriza corrida;
5. apenas jogador correto consegue jogar;
6. servidor gera dado;
7. posição é atualizada;
8. outro cliente recebe/consulta novo estado;
9. turno alterna;
10. primeiro a atingir 30 vence;
11. ações inválidas são rejeitadas;
12. dois clientes não conseguem corromper o estado.

Somente depois adicionar complexidade.

---

# 29. Features V2 possíveis

Não implementar sem o MVP pronto.

Possibilidades:

- DRS;
- boost;
- safety car;
- pit stop;
- pneu furado;
- slipstream/vácuo;
- eventos aleatórios;
- seleção de carro;
- escolha de circuito;
- revanche;
- streaming gRPC;
- reconexão;
- múltiplas salas.

Evitar scope creep.

---

# 30. Eventos especiais

Por enquanto **NÃO fazem parte do MVP**.

Se forem implementados posteriormente, devem continuar sendo decididos pelo servidor.

Exemplo:

```text
position = 15

event = DRS

next_roll_bonus = +1
```

Nunca implementar uma regra real exclusivamente no Pygame.

---

# 31. Tratamento visual de rede

O frontend precisa ser capaz de apresentar estados como:

```text
CONNECTING
WAITING_FOR_PLAYER
READY
MY_TURN
OPPONENT_TURN
ROLLING
MOVING
FINISHED
CONNECTION_ERROR
```

Não congelar a interface enquanto espera chamadas de rede.

Chamadas gRPC não devem bloquear o loop principal do Pygame por períodos perceptíveis.

---

# 32. Game loop

O loop do Pygame deve permanecer conceitualmente:

```text
INPUT
  ↓
UPDATE
  ↓
NETWORK STATE
  ↓
ANIMATION
  ↓
RENDER
```

Evitar misturar regras do servidor dentro do render.

---

# 33. Resolução

Ainda deve ser validada durante o protótipo.

Preferir uma resolução base fixa adequada a pixel art, escalada para a janela quando necessário.

Exemplos possíveis:

```text
960x540
1280x720
```

Não assumir resolução final antes de testar os assets existentes.

---

# 34. Organização de código

Preferir:

- funções pequenas;
- responsabilidades claras;
- classes apenas quando fizerem sentido;
- nomes explícitos;
- type hints quando úteis;
- constantes para configuração;
- evitar números mágicos;
- não adicionar comentários nem docstrings no código; nomes claros devem bastar.

Evitar abstrações prematuras.

---

# 35. Git

Trabalhar incrementalmente.

Exemplos de commits:

```text
feat: create pygame window
feat: add parallax background
feat: add car rendering
feat: add race hud
feat: add dice animation
feat: connect grpc client
fix: preserve pixel scaling
```

Não fazer uma implementação gigantesca em um único commit.

---

# 36. Antes de modificar código

Claude deve:

1. inspecionar a estrutura existente;
2. identificar os arquivos relevantes;
3. verificar assets reais;
4. entender o fluxo atual;
5. alterar apenas o necessário;
6. executar/testar quando possível;
7. informar arquivos modificados e comportamento resultante.

Nunca assumir que um arquivo existe apenas porque aparece neste documento.

---

# 37. Ao encontrar ambiguidades

Não inventar regras importantes.

Se houver dúvida que afete:

- protocolo;
- regras;
- arquitetura;
- estado;
- comportamento multiplayer;

apresente as opções e peça decisão.

Para detalhes pequenos de frontend, escolha uma solução razoável e mantenha consistência visual.

---

# 38. Prioridade acadêmica

Este projeto precisa ser fácil de **explicar e defender**.

Uma solução simples e compreendida pelo grupo é melhor do que uma arquitetura sofisticada copiada sem entendimento.

Pergunta que deve orientar decisões:

> "Os integrantes conseguem explicar por que isso existe e como funciona?"

Se não, simplificar.

---

# 39. Princípios finais

1. **Servidor é autoritativo.**
2. **Cliente solicita; servidor decide.**
3. **Pygame apresenta; não governa as regras.**
4. **gRPC é o canal principal de comunicação.**
5. **Estado compartilhado precisa ser consistente.**
6. **Concorrência é parte central do trabalho.**
7. **Backend deve permanecer pequeno e compreensível.**
8. **Frontend pode ser visualmente ambicioso.**
9. **MVP antes de features extras.**
10. **Toda implementação deve permanecer compreensível e justificável pelo grupo.**

---

# 40. Primeira tarefa ao iniciar o desenvolvimento

Começar pelo **protótipo visual offline do cliente**.

Objetivo imediato:

```text
1. Inicializar Pygame
2. Criar janela
3. Definir resolução base
4. Carregar assets existentes
5. Montar background em camadas
6. Montar pista
7. Renderizar carro vermelho
8. Renderizar carro azul
9. Criar parallax básico
10. Criar HUD provisório
```

Não integrar gRPC ainda.

Quando essa tela estiver funcionando, utilizar dados mockados para testar:

```text
Player 1 position = 12
Player 2 position = 9
Current turn = Player 1
Dice result = 4
```

A partir daí, evoluir incrementalmente.

---

## Contexto resumido para novas sessões

Se estiver retomando este projeto em uma nova sessão:

> Estamos construindo um jogo acadêmico de Sistemas Distribuídos chamado Distributed Racing. É uma corrida pixel art para dois jogadores feita com Python + Pygame no cliente e Python + gRPC no servidor. A corrida funciona em turnos: o cliente solicita uma jogada, o servidor autoritativo gera um dado de 1 a 6, atualiza a posição lógica (0–30), verifica vitória e troca o turno. O foco acadêmico é RPC, estado compartilhado, concorrência e sincronização. O frontend representa isso como uma corrida lateral inspirada visualmente em automobilismo/F1, com parallax, carros vermelho e azul, HUD e animações. IA pode auxiliar em todas as etapas do desenvolvimento, incluindo frontend, backend, testes e documentação. O primeiro objetivo é construir o protótipo Pygame offline usando os assets existentes e dados mockados.
