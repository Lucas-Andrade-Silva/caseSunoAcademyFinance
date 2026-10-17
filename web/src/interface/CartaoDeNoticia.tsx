// O cartão de uma notícia (uma Ata): data, título e as primeiras linhas do resumo. Na Ingestão
// ele abre o texto e tem a bolinha de seleção; no popup de confirmação é só leitura.
import type { ResumoDaAta } from "../dados/cliente";
import { seloDaAta } from "../lib/fontes";
import { formatarDataDoDia } from "../texto/rotulos";
import { IconeMarca } from "./Icones";

export function Bolinha({
  marcada,
  desabilitada,
  onClick,
  rotulo,
}: {
  marcada: boolean;
  desabilitada?: boolean;
  onClick: () => void;
  rotulo: string;
}) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={marcada}
      aria-label={rotulo}
      disabled={desabilitada}
      onClick={(evento) => {
        evento.stopPropagation();
        onClick();
      }}
      className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-30 ${
        marcada ? "border-white bg-white text-ilha" : "border-[#555] text-transparent hover:border-claro"
      }`}
    >
      <IconeMarca size={15} strokeWidth={2.5} />
    </button>
  );
}

interface Propriedades {
  ata: ResumoDaAta;
  onAbrir?: () => void;
  marcada?: boolean;
  /** Presente só quando o cartão tem a bolinha. */
  onMarcar?: () => void;
  bolinhaDesabilitada?: boolean;
}

export default function CartaoDeNoticia({
  ata,
  onAbrir,
  marcada = false,
  onMarcar,
  bolinhaDesabilitada,
}: Propriedades) {
  const selo = seloDaAta(ata.categoria);
  const conteudo = (
    <>
      <span className={`flex items-start justify-between gap-3 ${onMarcar ? "min-h-6 pr-9" : ""}`}>
        <span className="text-[13px] text-etiqueta">
          {formatarDataDoDia(ata.data_referencia)}
          {selo && <span className="ml-2 text-coral-claro">{selo}</span>}
          {!ata.extracao_completa && (
            <span className="ml-2 text-coral-claro" title="Texto curto demais e sem número: não há afirmação para conferir, a geração recusa.">
              texto curto
            </span>
          )}
          {ata.extracao_completa && ata.qualitativa && (
            <span className="ml-2 text-etiqueta" title="Sem número no texto: o conteúdo sai qualitativo, só com afirmações da própria notícia.">
              sem número · conteúdo qualitativo
            </span>
          )}
        </span>
      </span>
      <span className="mt-3 block text-[17px] leading-snug text-texto">{ata.titulo}</span>
      {ata.resumo && (
        <span className="mt-2.5 line-clamp-4 block text-[14px] leading-relaxed text-etiqueta">
          {ata.resumo}
        </span>
      )}
    </>
  );

  const base = `relative block w-full rounded-xl text-left transition-colors duration-150 ${
    marcada ? "bg-superficie-alta ring-1 ring-claro/60" : "bg-superficie"
  }`;
  return (
    <div className={base}>
      {onAbrir ? (
        <button type="button" onClick={onAbrir} aria-label={`Abrir ${ata.titulo}`} className="block w-full rounded-xl p-5 text-left hover:bg-superficie-alta">
          {conteudo}
        </button>
      ) : (
        <div className="p-5">{conteudo}</div>
      )}
      {onMarcar && (
        <div className="absolute right-5 top-5">
          <Bolinha
            marcada={marcada}
            desabilitada={bolinhaDesabilitada}
            onClick={onMarcar}
            rotulo={`Selecionar ${ata.titulo}`}
          />
        </div>
      )}
    </div>
  );
}
