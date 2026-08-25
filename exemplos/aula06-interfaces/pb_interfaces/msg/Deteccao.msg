# Uma deteccao individual na cena.
#
# Compare com o que o TP1 publicava: um std_msgs/Int32 valendo 3.
# "3" nao diz tres de que, com que certeza, nem onde. Esta mensagem diz.

string  classe        # rotulo do SEU dominio: "tomate_maduro", "vaga_livre", "peca_ok"
float32 confianca     # 0.0 a 1.0 -- quanto o detector acredita nisso
int32   x             # centro do objeto, em pixels da imagem
int32   y
int32   area          # area em pixels: separa objeto de respingo
