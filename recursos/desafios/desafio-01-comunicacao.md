# Desafio semanal 1 — Comunicação em ROS 2 (opcional, treino p/ o TP1)

Partindo do exemplo `aula02-comunicacao`:

1. Crie um **segundo publisher** que publique em `/camera/status` a uma frequência diferente (ex.: 0,5 s) — observe os dois fluxos chegando no assinante.
2. Faça o `assinante` **só logar** mensagens que contenham a palavra "objeto(s)" com número > 0 (filtro simples).
3. Adicione um **parâmetro** `frequencia_hz` ao publicador (como no `pacote_minimo`) e mostre a alteração dinâmica com `ros2 param set`.
4. Chame o serviço `/contagem` e confira que o total bate com o que você viu no `ros2 topic echo`.
5. Faça um `rqt_graph`, salve a captura em `docs/evidencias/` do seu repositório e dê push na `dev`.

**Entrega (opcional):** comente no Infnet.Online que fez, com o link do commit. Sem nota — é aquecimento para o TP1.
