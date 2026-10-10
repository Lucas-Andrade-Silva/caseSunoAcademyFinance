// A Matriz 3×3 em miniatura: a posição do quadradinho é a posição da Célula (Audiências nas
// linhas, Formatos nas colunas). Dá, num relance, o que foi pedido e como está cada Célula.
import { AUDIENCIAS, FORMATOS, type PosicaoResumo } from "../dados/cliente";
import { chaveDaPosicao, estadoDaPosicao, type EstadoPosicao } from "../lib/matriz";

const COR_DO_QUADRADO: Record<EstadoPosicao, string> = {
  aprovada: "border-ok bg-ok",
  aguardando: "border-[#5a5a60] bg-[#5a5a60]",
  revisao: "border-alerta bg-alerta",
  reprovada: "border-suno bg-suno",
};

const TEXTO_DO_ESTADO: Record<EstadoPosicao, string> = {
  aprovada: "você aprovou",
  aguardando: "espera a sua decisão",
  revisao: "revisão humana",
  reprovada: "reprovada ou parou",
};

export default function MiniMatriz({ posicoes }: { posicoes: PosicaoResumo[] }) {
  const porPosicao = new Map(posicoes.map((p) => [chaveDaPosicao(p.audiencia, p.formato), p]));
  return (
    <div
      className="grid shrink-0 grid-cols-3 grid-rows-3 gap-1"
      role="img"
      aria-label={`Matriz: ${posicoes.length} de 9 Células pedidas`}
    >
      {AUDIENCIAS.flatMap((audiencia) =>
        FORMATOS.map((formato) => {
          const posicao = porPosicao.get(chaveDaPosicao(audiencia, formato));
          const classe = posicao
            ? COR_DO_QUADRADO[estadoDaPosicao(posicao)]
            : "border-dashed border-[#3b3b40]";
          const titulo = posicao ? TEXTO_DO_ESTADO[estadoDaPosicao(posicao)] : "não pedida";
          return (
            <span
              key={`${audiencia}:${formato}`}
              title={titulo}
              className={`block h-[17px] w-[17px] rounded border-[1.5px] ${classe}`}
            />
          );
        }),
      )}
    </div>
  );
}

export function LegendaMiniMatriz() {
  const itens: ReadonlyArray<{ classe: string; texto: string }> = [
    { classe: "border-ok bg-ok", texto: "você aprovou" },
    { classe: "border-[#5a5a60] bg-[#5a5a60]", texto: "espera a sua decisão" },
    { classe: "border-alerta bg-alerta", texto: "revisão humana" },
    { classe: "border-suno bg-suno", texto: "reprovada ou parou" },
    { classe: "border-dashed border-[#3b3b40]", texto: "não pedida" },
  ];
  return (
    <div className="mt-5 flex flex-wrap items-center gap-x-4 gap-y-1.5 border-t border-linha pt-3 text-[11px] text-suave">
      <span>Mini-Matriz:</span>
      {itens.map((entrada) => (
        <span key={entrada.texto} className="flex items-center gap-1.5">
          <span
            className={`inline-block h-[11px] w-[11px] rounded-[3px] border-[1.5px] ${entrada.classe}`}
          />
          {entrada.texto}
        </span>
      ))}
    </div>
  );
}
