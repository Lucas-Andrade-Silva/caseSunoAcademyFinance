// Os quadros do carrossel, um por linha: o texto escrito (papel, título, corpo, destaque, dado) e como
// deve ser a imagem daquele quadro. A linha fecha e abre; a primeira já vem aberta.
import { useState, type ReactNode } from "react";
import { IconeBaixo } from "../../interface/Icones";
import { Quadrado, type CorDoQuadrado } from "../../interface/Linha";
import { papelDoQuadro, rotuloDaComposicao, rotuloDoPapel, type PapelDoQuadro } from "./composicoes";
import { direcaoDaImagem } from "./direcaoDaImagem";
import { rotuloDoIcone } from "./idsDeIcones";
import type { AncoraDeQuadro, QuadroMontado } from "./modelo";

const COR_DO_PAPEL: Record<PapelDoQuadro, CorDoQuadrado> = {
  hook: "coral",
  ponto: "azul",
  citacao: "roxo",
  cta: "amarelo",
};

function Dado({ nome, children }: { nome: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-[12px] font-medium uppercase tracking-[0.02em] text-etiqueta">{nome}</dt>
      <dd className="mt-1 text-[14px] leading-relaxed text-claro">{children}</dd>
    </div>
  );
}

function textoDoDado(chave: string, ancoras: readonly AncoraDeQuadro[]): string {
  const ancora = ancoras.find((a) => a.chave === chave);
  return ancora ? `${ancora.rotulo} · ${ancora.citacao}` : `${chave} · sem valor`;
}

function LinhaDoQuadro({
  quadro,
  ancoras,
  aberta,
  aoAlternar,
}: {
  quadro: QuadroMontado;
  ancoras: readonly AncoraDeQuadro[];
  aberta: boolean;
  aoAlternar: () => void;
}) {
  const { slide, composicao, indice, total, grafico, icones } = quadro;
  const papel = papelDoQuadro(slide);
  const idDoCorpo = `quadro-${indice}`;
  return (
    <li className="rounded-lg bg-superficie">
      <button
        type="button"
        onClick={aoAlternar}
        aria-expanded={aberta}
        aria-controls={idDoCorpo}
        className="flex h-[70px] w-full items-center gap-4 rounded-lg px-[21px] text-left transition-colors duration-150 hover:bg-superficie-alta"
      >
        <Quadrado cor={COR_DO_PAPEL[papel]}>
          <span className="text-[16px] font-semibold tabular-nums">{indice + 1}</span>
        </Quadrado>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[17px] leading-tight text-texto">{slide.titulo}</span>
          <span className="mt-0.5 block truncate text-[13px] leading-tight text-etiqueta">
            {rotuloDoPapel(papel)} · {rotuloDaComposicao(composicao)}
          </span>
        </span>
        <IconeBaixo
          size={20}
          className={`shrink-0 text-claro transition-transform duration-200 ease-[var(--ease-saida)] motion-reduce:transition-none ${
            aberta ? "rotate-180" : ""
          }`}
        />
      </button>
      {aberta && (
        <div id={idDoCorpo} className="px-[21px] pb-6 pt-1">
          <p className="text-[15px] leading-relaxed text-claro">{slide.corpo}</p>
          <dl className="mt-5 grid gap-4">
            {slide.destaque && <Dado nome="Destaque">{slide.destaque}</Dado>}
            {slide.dado && <Dado nome="Dado">{textoDoDado(slide.dado, ancoras)}</Dado>}
            {icones.length > 0 && <Dado nome="Ícones">{icones.map(rotuloDoIcone).join(" · ")}</Dado>}
            <Dado nome="Imagem">{direcaoDaImagem(slide, composicao, indice, total, grafico)}</Dado>
          </dl>
        </div>
      )}
    </li>
  );
}

export default function Quadros({
  quadros,
  ancoras,
}: {
  quadros: readonly QuadroMontado[];
  ancoras: readonly AncoraDeQuadro[];
}) {
  const [abertas, definirAbertas] = useState<ReadonlySet<number>>(() => new Set([0]));

  function alternar(indice: number) {
    definirAbertas((atuais) => {
      const proximas = new Set(atuais);
      if (proximas.has(indice)) proximas.delete(indice);
      else proximas.add(indice);
      return proximas;
    });
  }

  if (quadros.length === 0) return <p className="py-2 text-[15px] text-etiqueta">Sem quadros.</p>;
  return (
    <ul className="flex flex-col gap-2.5">
      {quadros.map((quadro) => (
        <LinhaDoQuadro
          key={quadro.indice}
          quadro={quadro}
          ancoras={ancoras}
          aberta={abertas.has(quadro.indice)}
          aoAlternar={() => alternar(quadro.indice)}
        />
      ))}
    </ul>
  );
}
