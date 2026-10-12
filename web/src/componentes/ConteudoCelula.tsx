// O conteúdo de uma Célula, por Formato: Markdown, slides de carrossel ou blocos de roteiro.
// Cada slide mostra a chave da Âncora que ele cita (`dado`). O carrossel pode ser visto com o
// design embutido (templates e paleta do render, ADR 0020), ligado e desligado à vontade.
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import type { Audiencia, BlocoFala, Conteudo } from "../dados/cliente";
import { rotuloDaDirecao, rotuloDaDuracao } from "../texto/rotulos";
import Chip from "./Chip";
import PainelDoPlano from "./PainelDoPlano";
import PreviaCarrossel from "./PreviaCarrossel";

/** Onde buscar o plano de edição: só um Roteiro aprovado tem. */
interface OrigemDoPlano {
  identificador: string;
  audiencia: Audiencia;
}

/** A direção de cena de um bloco, em chips; o que é o padrão (corte, sem efeito) não aparece. */
function DirecaoDaCena({ bloco }: { bloco: BlocoFala }) {
  const sons = [bloco.som_de_entrada, bloco.som_de_efeito].filter((som) => som != null);
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {bloco.cena && <Chip tom="forte">{rotuloDaDirecao(bloco.cena)}</Chip>}
      {bloco.icone && <Chip>ícone: {rotuloDaDirecao(bloco.icone)}</Chip>}
      {bloco.entrada && bloco.entrada !== "corte" && (
        <Chip>entra: {rotuloDaDirecao(bloco.entrada)}</Chip>
      )}
      {bloco.tela && bloco.texto_anima && (
        <Chip>
          texto: {rotuloDaDirecao(bloco.texto_anima)} em {(bloco.texto_entra_em_s ?? 0).toFixed(1)}s
        </Chip>
      )}
      {bloco.efeito && bloco.efeito !== "nenhum" && (
        <Chip>efeito: {rotuloDaDirecao(bloco.efeito)}</Chip>
      )}
      {sons.map((som) => (
        <Chip key={som}>som: {rotuloDaDirecao(som)}</Chip>
      ))}
    </div>
  );
}

function CarrosselDaCelula({ slides }: { slides: NonNullable<Conteudo["slides"]> }) {
  const [comDesign, definirComDesign] = useState(false);
  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-xs text-suave">
        <input
          type="checkbox"
          checked={comDesign}
          onChange={(evento) => definirComDesign(evento.target.checked)}
        />
        Ver com o design do carrossel
      </label>
      {comDesign ? (
        <PreviaCarrossel slides={slides} />
      ) : (
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          {slides.map((slide, indice) => (
            <div
              key={indice}
              className="flex min-h-[158px] flex-col gap-1 rounded-xl border border-[#3a2323] bg-linear-to-br from-[#34191a] to-[#1b1011] p-3"
            >
              <span className="text-[9.5px] font-bold tracking-wider text-[#c98f8a]">
                {indice + 1} / {slides.length}
                {slide.tipo ? ` · ${slide.tipo}` : ""}
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
      )}
    </div>
  );
}

export default function ConteudoCelula({
  conteudo,
  plano,
}: {
  conteudo: Conteudo;
  plano?: OrigemDoPlano;
}) {
  if (conteudo.formato === "texto_analitico") {
    return (
      <article className="markdown rounded-2xl bg-cartao p-4">
        <ReactMarkdown>{conteudo.texto ?? ""}</ReactMarkdown>
      </article>
    );
  }

  if (conteudo.formato === "carrossel") {
    return <CarrosselDaCelula slides={conteudo.slides ?? []} />;
  }

  const blocos = conteudo.blocos ?? [];
  const estimada = blocos.length > 0 ? blocos[blocos.length - 1].fim_s : null;
  return (
    <div>
      <p className="mb-2 text-xs text-suave">
        {blocos.length} {blocos.length === 1 ? "cena" : "cenas"} · {rotuloDaDuracao(estimada ? Math.round(estimada) : null)}{" "}
        estimados
        {conteudo.duracao_alvo_s ? ` · alvo ${rotuloDaDuracao(conteudo.duracao_alvo_s)}` : ""}
      </p>
      <ol className="space-y-2">
        {blocos.map((bloco, indice) => (
          <li key={indice} className="rounded-xl bg-cartao p-3">
            <p className="text-xs font-semibold text-suave">
              {indice + 1} · {bloco.inicio_s.toFixed(1)}s – {bloco.fim_s.toFixed(1)}s
            </p>
            <p className="mt-1 text-sm">{bloco.fala}</p>
            {bloco.tela && <p className="mt-1 text-xs italic text-suave">{bloco.tela}</p>}
            <DirecaoDaCena bloco={bloco} />
          </li>
        ))}
      </ol>
      {plano && <PainelDoPlano identificador={plano.identificador} audiencia={plano.audiencia} />}
    </div>
  );
}
