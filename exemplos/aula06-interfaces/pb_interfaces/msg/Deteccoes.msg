# O que a percepcao viu em UM quadro.
#
# O Header nao e enfeite: ele carrega o instante (stamp) e o referencial
# (frame_id). Sem stamp voce nao consegue dizer se a deteccao e de agora ou
# de tres segundos atras; sem frame_id voce nao consegue combinar esta
# informacao com a de outro sensor. Toda mensagem de percepcao leva Header.

std_msgs/Header header
Deteccao[]       deteccoes    # array de tamanho variavel
uint32           total        # redundante com deteccoes.size(), e de proposito:
                              # quem so quer contar nao precisa desempacotar o array
