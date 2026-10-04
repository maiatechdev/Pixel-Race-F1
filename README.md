# Distributed Racing

Jogo de corrida em pixel art para 2 jogadores, feito para a disciplina de Sistemas Distribuídos.

Os jogadores se revezam pedindo ao servidor para jogar o dado. O servidor sorteia o valor, move o carro, troca o turno e decide quem venceu. Os clientes só mostram o estado que recebem. Vence quem chegar primeiro à posição 30.

- **Servidor:** Python + gRPC
- **Cliente:** Python + Pygame (pygame-ce)
- **Contrato:** Protocol Buffers ([proto/racing.proto](proto/racing.proto))

## Instalação

É preciso ter Python 3.10 ou superior (o projeto foi testado no 3.14).

```
git clone https://github.com/maiatechdev/Pixel-Race-F1.git
cd Pixel-Race-F1
python -m venv .venv
```

Ative o ambiente virtual:

- Windows: `.venv\Scripts\activate`
- Linux/macOS: `source .venv/bin/activate`

E instale as dependências:

```
pip install -r requirements.txt
```

Usamos o `pygame-ce` no lugar do `pygame` porque o `pygame` original ainda não instala no Python 3.14. O código continua usando `import pygame`.

## Como jogar

Abra três terminais com o ambiente virtual ativado, na raiz do projeto.

1. Servidor:

   ```
   python server/server.py
   ```

   Ele escuta em `0.0.0.0:50051`. Para trocar a porta, use `--port`.

2. Primeiro jogador:

   ```
   python client/main.py --name Gabriel
   ```

3. Segundo jogador:

   ```
   python client/main.py --name Lucas
   ```

Na tela de conexão, confira nome, servidor e porta e aperte **Enter**. As opções `--name`, `--host` e `--port` só preenchem esses campos.

A corrida começa sozinha quando o segundo jogador entra. Depois da sequência de largada, cada jogador aperta **Espaço** (ou clica no botão) para jogar o dado na sua vez. **Esc** sai do jogo.

### Em computadores diferentes

1. No computador do servidor, descubra o IP na rede local (`ipconfig` no Windows, `ip addr` no Linux). Algo como `192.168.0.15`.
2. Rode o servidor nesse computador. Se o Windows perguntar sobre o firewall, permita o acesso em redes privadas.
3. Nos outros computadores, abra o cliente e coloque esse IP no campo **Servidor**, ou use `--host 192.168.0.15`.

Todos precisam estar na mesma rede. Algumas redes Wi-Fi (de faculdade, por exemplo) bloqueiam a conexão entre aparelhos; nesse caso, um hotspot de celular resolve.

## Testes

```
python -m unittest discover -s server
```

São testes da regra do jogo, de concorrência e de integração pelo gRPC, com dois clientes conectados a um servidor real.

## Como funciona

### Contrato gRPC

| RPC | O que faz |
|---|---|
| `JoinGame(name)` | Entra na partida e devolve `player_id` e um `token` secreto |
| `GetGameState(token)` | Devolve o estado atual da partida |
| `RollDice(token)` | Pede para jogar o dado; o servidor sorteia e devolve o valor e o novo estado |
| `LeaveGame(token)` | Sai da partida |

O cliente nunca envia valor de dado nem posição. Ele só envia o token, e o servidor descobre quem é o jogador a partir dele.

Erros usam os códigos de status do próprio gRPC:

| Situação | Código |
|---|---|
| Nome vazio | `INVALID_ARGUMENT` |
| Sala cheia | `RESOURCE_EXHAUSTED` |
| Token inválido | `UNAUTHENTICATED` |
| Fora do turno, ou corrida não está em andamento | `FAILED_PRECONDITION` |

### Servidor

- [server/game.py](server/game.py) tem toda a regra da partida e não depende do gRPC.
- [server/server.py](server/server.py) só converte entre as mensagens gRPC e o `Game`.

O gRPC atende cada chamada numa thread separada. Por isso, cada operação do `Game` roda inteira dentro de um `threading.Lock`. A parte crítica é o `RollDice`: verificar o turno, sortear o dado, mover o carro e trocar o turno precisam acontecer como um bloco só. Sem o lock, duas chamadas simultâneas do mesmo jogador poderiam passar as duas pela verificação do turno, e ele jogaria duas vezes.

O teste `test_simultaneous_rolls_by_same_player_count_once` dispara 50 chamadas `RollDice` ao mesmo tempo para o mesmo jogador e verifica que só uma é aceita. Medimos que, sem o lock, as 50 são aceitas.

Outras regras do servidor:

- A corrida começa quando o segundo jogador entra.
- Se um jogador sai, ou fica mais de 5 segundos sem falar com o servidor, o adversário vence por W.O.
- Depois que a corrida termina, a sala só aceita novos jogadores quando os dois saem.

### Cliente

- [client/network.py](client/network.py) faz todas as chamadas gRPC numa thread separada, para a tela nunca travar esperando a rede. Os resultados chegam ao loop do Pygame por uma fila.
- A cada 250 ms o cliente consulta o estado (polling). Essa consulta também avisa o servidor de que o jogador continua conectado.
- [client/screens/race.py](client/screens/race.py) só desenha o que o servidor mandou. Quando a posição de um jogador muda, a tela anima o dado e o carro até a nova posição.

A posição lógica (0 a 30) é do servidor. A posição do carro na tela é só interpolação visual.

## Estrutura

```
proto/racing.proto       contrato gRPC
server/                  servidor, regra do jogo e testes
client/                  cliente Pygame
  main.py                ponto de entrada
  network.py             comunicação com o servidor
  screens/               tela de conexão e tela da corrida
  components/            carro, dado, HUD, parallax, largada, chegada
assets/                  imagens usadas pelo jogo
assets_originais/        imagens originais, antes do tratamento
gerar_proto.py           regenera o código gRPC a partir do .proto
tratar_assets.py         gera assets/ a partir de assets_originais/
```

Se o `.proto` mudar, rode `python gerar_proto.py` para atualizar o código gerado em `server/` e em `client/`.

As imagens originais vieram com o fundo xadrez desenhado nos pixels, sem transparência de verdade. O `tratar_assets.py` remove esse fundo, recorta e reduz as imagens para o tamanho do jogo. Ele só precisa rodar de novo se alguma imagem de `assets_originais/` mudar.

## Licença

MIT. Veja [LICENSE](LICENSE).
