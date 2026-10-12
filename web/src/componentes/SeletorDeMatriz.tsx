// A Matriz 3×3 clicável do passo "Configurar": clique numa Célula, no nome de uma Audiência
// (linha) ou no de um Formato (coluna). Duas listas de múltipla escolha só montariam retângulos;
// a Matriz permite combinações soltas (spec do front, seção 4.2).
import {
  alternarCelula,
  alternarColuna,
  alternarLinha,
  AUDIENCIAS_NA_ORDEM,
  colunaCompleta,
  estaSelecionada,
  FORMATOS_NA_ORDEM,
  linhaCompleta,
  type Posicao,
} from "../lib/pedido";
import { rotuloAudiencia, rotuloFormato } from "../texto/rotulos";

const CABECALHO =
  "rounded-lg bg-cartao px-1 py-1 text-center text-[10.5px] font-bold uppercase tracking-wider transition hover:bg-cartao-2";

export default function SeletorDeMatriz({
  selecao,
  onMudar,
  desabilitado = false,
}: {
  selecao: Posicao[];
  onMudar: (nova: Posicao[]) => void;
  desabilitado?: boolean;
}) {
  return (
    <div className="grid grid-cols-[78px_repeat(3,minmax(0,1fr))] sm:grid-cols-[84px_repeat(3,minmax(0,1fr))] gap-2">
      <div />
      {FORMATOS_NA_ORDEM.map((formato) => (
        <button
          key={formato}
          type="button"
          disabled={desabilitado}
          aria-pressed={colunaCompleta(selecao, formato)}
          onClick={() => onMudar(alternarColuna(selecao, formato))}
          className={`${CABECALHO} ${colunaCompleta(selecao, formato) ? "text-texto" : "text-suave"}`}
        >
          {rotuloFormato(formato)}
        </button>
      ))}
      {AUDIENCIAS_NA_ORDEM.map((audiencia) => (
        <LinhaDaMatriz
          key={audiencia}
          audiencia={audiencia}
          selecao={selecao}
          onMudar={onMudar}
          desabilitado={desabilitado}
        />
      ))}
    </div>
  );
}

function LinhaDaMatriz({
  audiencia,
  selecao,
  onMudar,
  desabilitado,
}: {
  audiencia: string;
  selecao: Posicao[];
  onMudar: (nova: Posicao[]) => void;
  desabilitado: boolean;
}) {
  return (
    <>
      <button
        type="button"
        disabled={desabilitado}
        aria-pressed={linhaCompleta(selecao, audiencia)}
        onClick={() => onMudar(alternarLinha(selecao, audiencia))}
        className={`flex items-center rounded-lg bg-cartao px-2 text-left text-xs font-bold transition hover:bg-cartao-2 ${
          linhaCompleta(selecao, audiencia) ? "text-texto" : "text-suave"
        }`}
      >
        {rotuloAudiencia(audiencia)}
      </button>
      {FORMATOS_NA_ORDEM.map((formato) => {
        const marcada = estaSelecionada(selecao, { audiencia, formato });
        return (
          <button
            key={formato}
            type="button"
            disabled={desabilitado}
            aria-pressed={marcada}
            aria-label={`${rotuloAudiencia(audiencia)} · ${rotuloFormato(formato)}`}
            onClick={() => onMudar(alternarCelula(selecao, { audiencia, formato }))}
            className={`flex min-h-[58px] items-center justify-center rounded-xl border-[1.5px] text-[11px] transition ${
              marcada
                ? "border-suno bg-suno/15 font-bold text-texto"
                : "border-dashed border-[#3b3b40] text-[#5d5d63] hover:border-[#55555b]"
            }`}
          >
            {marcada ? (
              <>
                <span className="mr-1 text-suno">✓</span>
                {rotuloFormato(formato)}
              </>
            ) : (
              "—"
            )}
          </button>
        );
      })}
    </>
  );
}
