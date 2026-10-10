// O conteúdo de uma Célula, por Formato: Markdown, slides de carrossel ou blocos de roteiro.
// Cada slide mostra a chave da Âncora que ele cita (`dado`).
import ReactMarkdown from "react-markdown";
import type { Conteudo } from "../dados/cliente";
import Chip from "./Chip";

export default function ConteudoCelula({ conteudo }: { conteudo: Conteudo }) {
  if (conteudo.formato === "texto_analitico") {
    return (
      <article className="markdown rounded-2xl bg-cartao p-4">
        <ReactMarkdown>{conteudo.texto ?? ""}</ReactMarkdown>
      </article>
    );
  }

  if (conteudo.formato === "carrossel") {
    const slides = conteudo.slides ?? [];
    return (
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {slides.map((slide, indice) => (
          <div
            key={indice}
            className="flex min-h-[158px] flex-col gap-1 rounded-xl border border-[#3a2323] bg-linear-to-br from-[#34191a] to-[#1b1011] p-3"
          >
            <span className="text-[9.5px] font-bold tracking-wider text-[#c98f8a]">
              {indice + 1} / {slides.length}
            </span>
            <strong className="text-[12.5px] leading-tight">{slide.titulo}</strong>
            <p className="text-[11px] leading-snug text-[#d6c3c1]">{slide.corpo}</p>
            {slide.dado && (
              <span className="mt-auto self-start">
                <Chip tom="ruim">{slide.dado}</Chip>
              </span>
            )}
          </div>
        ))}
      </div>
    );
  }

  return (
    <ol className="space-y-2">
      {(conteudo.blocos ?? []).map((bloco, indice) => (
        <li key={indice} className="rounded-xl bg-cartao p-3">
          <p className="text-xs font-semibold text-suave">
            {bloco.inicio_s.toFixed(1)}s – {bloco.fim_s.toFixed(1)}s
          </p>
          <p className="mt-1 text-sm">{bloco.fala}</p>
          {bloco.tela && <p className="mt-1 text-xs italic text-suave">{bloco.tela}</p>}
        </li>
      ))}
    </ol>
  );
}
