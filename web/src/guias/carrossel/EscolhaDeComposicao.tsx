// Os seis tipos de composição: escolha única. O valor vira `composicao_visual` no pedido.
import { COMPOSICOES } from "./composicoes";
import MiniaturaDaComposicao from "./MiniaturaDaComposicao";
import type { Composicao } from "./modelo";
import Opcao, { Opcoes } from "./Opcao";

export default function EscolhaDeComposicao({
  valor,
  aoEscolher,
}: {
  valor: Composicao;
  aoEscolher: (composicao: Composicao) => void;
}) {
  return (
    <Opcoes rotuloAcessivel="Tipo de composição" largura={150}>
      {COMPOSICOES.map((composicao) => (
        <Opcao
          key={composicao.valor}
          rotulo={composicao.rotulo}
          selecionada={composicao.valor === valor}
          onClick={() => aoEscolher(composicao.valor)}
          className="h-[112px]"
        >
          <MiniaturaDaComposicao composicao={composicao.valor} />
        </Opcao>
      ))}
    </Opcoes>
  );
}
