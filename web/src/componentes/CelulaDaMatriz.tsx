// Um cartão da Matriz da Saída aberta: só o estado (chip do Laudo e chip da decisão humana).
// O conteúdo mora na Célula aberta, um clique adiante.
import { Link } from "react-router-dom";
import type { PosicaoResumo } from "../dados/cliente";
import { chipsDaPosicao } from "../lib/matriz";
import { rotuloAudiencia, rotuloFormato } from "../texto/rotulos";
import Chip from "./Chip";

export default function CelulaDaMatriz({
  identificador,
  posicao,
}: {
  identificador: string;
  posicao: PosicaoResumo;
}) {
  const chips = chipsDaPosicao(posicao);
  return (
    <Link
      to={`/saidas/${encodeURIComponent(identificador)}/celulas/${posicao.audiencia}/${posicao.formato}`}
      className="flex min-h-[64px] flex-col justify-center gap-1.5 rounded-xl bg-cartao p-3 transition hover:ring-1 hover:ring-suno/50"
    >
      <span className="sr-only">
        {rotuloAudiencia(posicao.audiencia)} · {rotuloFormato(posicao.formato)}
      </span>
      <span className="flex flex-wrap gap-1">
        <Chip tom={chips.laudo.tom}>{chips.laudo.texto}</Chip>
      </span>
      <span className="flex flex-wrap gap-1">
        <Chip tom={chips.decisao.tom}>{chips.decisao.texto}</Chip>
      </span>
    </Link>
  );
}
