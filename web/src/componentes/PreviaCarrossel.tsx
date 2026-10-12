// Prévia do design do Carrossel: os mesmos quatro templates (hook, ponto, citação, CTA) e a
// paleta do render HTML/Puppeteer (ADR 0020), em miniatura. É só leitura — o PNG final sai do
// servidor ao aprovar. Paleta: #FF0000, #AF0404, #414141, #252525 e branco.
import type { Conteudo } from "../dados/cliente";

type Slide = NonNullable<Conteudo["slides"]>[number];

function Titulo({ slide }: { slide: Slide }) {
  const { titulo, destaque } = slide;
  if (!destaque || !titulo.includes(destaque)) return <>{titulo}</>;
  const [antes, ...resto] = titulo.split(destaque);
  return (
    <>
      {antes}
      <mark className="rounded bg-[#AF0404] px-1 text-white">{destaque}</mark>
      {resto.join(destaque)}
    </>
  );
}

function Miniatura({ slide, indice, total }: { slide: Slide; indice: number; total: number }) {
  const tipo = slide.tipo ?? "ponto";
  const tamanhoDoTitulo = tipo === "hook" ? "text-[17px]" : tipo === "cta" ? "text-[15px]" : "text-[13px]";
  return (
    <div
      data-tipo={tipo}
      className="relative flex aspect-[4/5] flex-col gap-1.5 overflow-hidden bg-[#252525] p-3 text-white"
    >
      <div className="absolute inset-x-0 top-0 h-[3px] bg-[#FF0000]" />
      <div className="flex items-center justify-between text-[8px]">
        <span className="rounded bg-[#AF0404] px-1.5 py-0.5 font-bold">{tipo}</span>
        <span>
          {indice + 1}/{total}
        </span>
      </div>
      {tipo === "citacao" && <span className="text-3xl font-bold leading-none text-[#FF0000]">“</span>}
      <strong className={`${tamanhoDoTitulo} mt-2 leading-tight`}>
        <Titulo slide={slide} />
      </strong>
      {tipo === "citacao" ? (
        <p className="mt-auto rounded-lg bg-[#414141] p-2 text-[10px] leading-snug">{slide.corpo}</p>
      ) : (
        <p className="text-[10px] leading-snug">{slide.corpo}</p>
      )}
      {slide.dado && (
        <span className="mt-auto self-start rounded bg-[#414141] px-1.5 py-0.5 text-[9px] font-bold">
          <span className="text-[#FF0000]">▮</span> {slide.dado}
        </span>
      )}
      {tipo === "cta" && (
        <span className="mt-auto self-start rounded-full bg-[#AF0404] px-2.5 py-1 text-[9px] font-bold">
          Leia a Ata completa
        </span>
      )}
      {tipo === "hook" && <div className="mt-auto h-[3px] w-8 rounded bg-[#FF0000]" />}
    </div>
  );
}

export default function PreviaCarrossel({ slides }: { slides: Slide[] }) {
  return (
    <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-4">
      {slides.map((slide, indice) => (
        <Miniatura key={indice} slide={slide} indice={indice} total={slides.length} />
      ))}
    </div>
  );
}
