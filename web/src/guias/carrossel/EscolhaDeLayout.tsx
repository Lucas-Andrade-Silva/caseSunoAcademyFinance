// Os tipos de uma família: os layouts dela, com a miniatura do post real. O escolhido vira o
// layout preferido; o servidor ainda põe em cada quadro o layout da família que cabe no papel dele.
import { urlDaImagemDaReferencia, type ReferenciaVisual } from "../../dados/cliente";
import Opcao, { Opcoes } from "./Opcao";

export default function EscolhaDeLayout({
  layouts,
  valor,
  aoEscolher,
}: {
  layouts: readonly ReferenciaVisual[];
  valor: string | null;
  aoEscolher: (referencia: ReferenciaVisual) => void;
}) {
  return (
    <Opcoes rotuloAcessivel="Tipo de layout da família" largura={150}>
      {layouts.map((referencia) => (
        <Opcao
          key={referencia.identificador}
          rotulo={referencia.titulo}
          selecionada={referencia.identificador === valor}
          onClick={() => aoEscolher(referencia)}
          className="h-[132px]"
        >
          {referencia.imagem_disponivel ? (
            <img
              src={urlDaImagemDaReferencia(referencia.identificador)}
              alt=""
              className="h-[72px] w-[58px] rounded-[3px] object-cover"
            />
          ) : (
            <span className="h-[72px] w-[58px] rounded-[3px] bg-superficie-alta" aria-hidden="true" />
          )}
        </Opcao>
      ))}
    </Opcoes>
  );
}
