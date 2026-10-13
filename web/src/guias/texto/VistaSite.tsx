// O texto como página de blog: barra de navegação, título grande, assinatura, o artigo e, ao lado,
// o índice "Neste texto" feito com os títulos das seções. Em área estreita o índice vai para cima.
import { useId } from "react";
import type { EstruturaDoTexto } from "./estrutura";
import TrechoHtml, { TituloHtml } from "./TrechoHtml";

function irPara(id: string): void {
  const reduzido = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.getElementById(id)?.scrollIntoView({ behavior: reduzido ? "auto" : "smooth", block: "start" });
}

export default function VistaSite({ estrutura, hoje }: { estrutura: EstruturaDoTexto; hoje: string }) {
  const prefixo = useId();
  const idDaSecao = (indice: number) => `${prefixo}-secao-${indice}`;
  const indice = estrutura.secoes.flatMap((secao, posicao) => (secao.titulo ? [{ titulo: secao.titulo, posicao }] : []));

  return (
    <article aria-label="Site" className="@container mx-auto w-full max-w-[1040px] overflow-hidden rounded-xl bg-white text-[#1a1a1a]">
      <div aria-hidden="true" className="flex h-14 items-center justify-between border-b border-[#e6e6e6] px-6 @3xl:px-12">
        <span className="text-[19px] font-extrabold tracking-[-0.01em]">Suno</span>
        <span className="hidden gap-7 text-[14px] text-[#5c5c5c] @md:flex">
          <span>Início</span>
          <span>Análises</span>
          <span>Sobre</span>
        </span>
      </div>

      <div className="px-6 pb-16 @3xl:px-12">
        <header className="max-w-[780px] pb-9 pt-10 @3xl:pt-14">
          <TituloHtml
            como="h2"
            html={estrutura.tituloHtml}
            atributos={estrutura.atributosDoTitulo}
            className="text-[34px] font-extrabold leading-[1.08] tracking-[-0.02em] @3xl:text-[48px]"
          />
          {estrutura.lide && (
            <TrechoHtml blocos={[estrutura.lide]} className="mt-5 [--corpo-cor:#444444] [--corpo-tamanho:20px]" />
          )}
          <p className="mt-7 flex items-center gap-3 text-[14px] text-[#5c5c5c]">
            <span
              aria-hidden="true"
              className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[#1a1a1a] text-[14px] font-semibold text-white"
            >
              S
            </span>
            <span>
              <strong className="font-semibold text-[#1a1a1a]">Suno</strong> · {hoje} · {estrutura.minutos} min de leitura
            </span>
          </p>
        </header>

        <div className="grid gap-10 border-t border-[#e6e6e6] pt-10 @3xl:grid-cols-[minmax(0,1fr)_210px]">
          <div className="min-w-0 max-w-[720px]">
            {estrutura.secoes.map((secao, posicao) => (
              <section key={posicao} id={idDaSecao(posicao)} className={`scroll-mt-4 ${posicao > 0 ? "mt-11" : ""}`}>
                {secao.titulo && (
                  <TituloHtml
                    como="h3"
                    html={secao.tituloHtml}
                    atributos={secao.atributosDoTitulo}
                    className="mb-3 text-[26px] font-bold leading-snug tracking-[-0.01em]"
                  />
                )}
                <TrechoHtml blocos={secao.blocos} className="[--corpo-tamanho:18px] [--corpo-entrelinha:1.7]" />
              </section>
            ))}
          </div>

          {indice.length > 1 && (
            <nav aria-label="Neste texto" className="order-first self-start @3xl:sticky @3xl:top-4 @3xl:order-none">
              <h3 className="text-[12px] font-bold uppercase tracking-[0.12em] text-[#5c5c5c]">Neste texto</h3>
              <ul className="mt-3 flex flex-col gap-2 border-l border-[#e6e6e6] pl-4">
                {indice.map((entrada) => (
                  <li key={entrada.posicao}>
                    <button
                      type="button"
                      onClick={() => irPara(idDaSecao(entrada.posicao))}
                      className="text-left text-[14px] leading-snug text-[#444444] transition-colors duration-150 hover:text-[#1a1a1a] hover:underline focus-visible:outline-[#1a1a1a]"
                    >
                      {entrada.titulo}
                    </button>
                  </li>
                ))}
              </ul>
            </nav>
          )}
        </div>
      </div>
    </article>
  );
}
