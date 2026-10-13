// Os exemplos de carrossel que a API tem (as referências visuais aprovadas): uma linha cada.
// Escolher um o mostra no celular da direita; escolher de novo desmarca.
import { urlDaImagemDaReferencia, type ReferenciaVisual } from "../../dados/cliente";
import { IconeMarca } from "../../interface/Icones";
import Linha from "../../interface/Linha";
import { ehComposicao, rotuloDaComposicao } from "./composicoes";
import MiniaturaDaComposicao from "./MiniaturaDaComposicao";

interface Propriedades {
  referencias: readonly ReferenciaVisual[] | undefined;
  erro: string | null;
  escolhida: string | null;
  aoEscolher: (referencia: ReferenciaVisual) => void;
}

export default function EscolhaDeExemplo({ referencias, erro, escolhida, aoEscolher }: Propriedades) {
  if (!referencias) {
    return erro ? (
      <p role="alert" className="py-2 text-[14px] leading-snug text-coral-claro">
        Não consegui buscar os exemplos. {erro}
      </p>
    ) : (
      <div className="flex flex-col gap-2.5" aria-hidden="true">
        {[0, 1, 2].map((indice) => (
          <span key={indice} className="pulsa h-[70px] rounded-lg bg-superficie" />
        ))}
      </div>
    );
  }
  const aprovadas = referencias.filter((referencia) => referencia.aprovada);
  if (aprovadas.length === 0) return <p className="py-2 text-[15px] text-etiqueta">Nenhum exemplo aprovado.</p>;
  return (
    <div className="flex flex-col gap-2.5">
      {aprovadas.map((referencia) => {
        const marcada = referencia.identificador === escolhida;
        return (
          <Linha
            key={referencia.identificador}
            cor="cinza"
            icone={
              ehComposicao(referencia.composicao) ? (
                <MiniaturaDaComposicao composicao={referencia.composicao} altura={24} />
              ) : referencia.imagem_disponivel ? (
                <img
                  src={urlDaImagemDaReferencia(referencia.identificador)}
                  alt=""
                  className="h-6 w-[19px] rounded-[2px] object-cover"
                />
              ) : null
            }
            titulo={referencia.titulo}
            subtitulo={`${referencia.tema} · ${rotuloDaComposicao(referencia.composicao)}`}
            fim={marcada ? <IconeMarca size={20} className="text-claro" /> : "seta"}
            selecionada={marcada}
            onClick={() => aoEscolher(referencia)}
          />
        );
      })}
    </div>
  );
}
