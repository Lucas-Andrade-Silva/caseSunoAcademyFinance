// O primeiro passo das configurações visuais: a Família visual. Suno escuro (o editor desenha, com
// paleta e ícones) ou uma das recriadas dos posts reais da Suno. A que não cobre os papéis dos
// quadros aparece apagada, com o motivo.
import { urlDaImagemDaReferencia } from "../../dados/cliente";
import type { OpcaoDeFamilia } from "./familias";
import MiniaturaDaComposicao from "./MiniaturaDaComposicao";
import Opcao, { Opcoes } from "./Opcao";

export default function EscolhaDeFamilia({
  opcoes,
  valor,
  aoEscolher,
}: {
  opcoes: readonly OpcaoDeFamilia[];
  valor: string;
  aoEscolher: (opcao: OpcaoDeFamilia) => void;
}) {
  return (
    <Opcoes rotuloAcessivel="Família visual" largura={150}>
      {opcoes.map((opcao) => {
        const capa = opcao.layouts.find((r) => r.imagem_disponivel);
        return (
          <Opcao
            key={opcao.valor}
            rotulo={opcao.rotulo}
            selecionada={opcao.valor === valor}
            indisponivel={opcao.indisponivel}
            onClick={() => aoEscolher(opcao)}
            className="min-h-[112px]"
          >
            {capa ? (
              <img
                src={urlDaImagemDaReferencia(capa.identificador)}
                alt=""
                className="h-[46px] w-[37px] rounded-[3px] object-cover"
              />
            ) : (
              <MiniaturaDaComposicao composicao="editorial" />
            )}
          </Opcao>
        );
      })}
    </Opcoes>
  );
}
