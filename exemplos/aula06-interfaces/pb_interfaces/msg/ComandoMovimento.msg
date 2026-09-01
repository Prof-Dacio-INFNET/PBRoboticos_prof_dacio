# O comando que iria para os motores. Hoje ele vira uma seta na tela.
#
# Esta mensagem existe para tornar visivel a fronteira entre PERCEBER e AGIR.
# O no que enxerga publica isto; quem age assina. Trocar a seta na tela por um
# driver de motor nao muda nem uma linha do lado da percepcao -- e essa
# separacao e a razao de o ROS 2 existir.

string  acao        # esquerda | direita | cima | baixo | frente | tras | parado | procurando
float32 erro_x      # -1.0 (alvo na borda esquerda) a +1.0 (borda direita)
float32 erro_y      # -1.0 (topo) a +1.0 (base)
float32 erro_area   # negativo = longe demais; positivo = perto demais
string  motivo      # por que esta acao, em portugues, para aparecer na tela
