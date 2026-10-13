// O texto como edição de newsletter: cabeçalho da publicação com a data de hoje, título, o bloco
// "Em resumo" (a primeira frase de cada seção) e as seções separadas por filete.
import { resumoDasSecoes, type EstruturaDoTexto } from "./estrutura";
import TrechoHtml, { TituloHtml } from "./TrechoHtml";

export default function VistaNewsletter({ estrutura, hoje }: { estrutura: EstruturaDoTexto; hoje: string }) {
  const topicos = resumoDasSecoes(estrutura);
  return (
    <article
      aria-label="Newsletter"
      className="@container mx-auto w-full max-w-[740px] rounded-xl bg-[#fbfaf6] px-6 py-10 text-[#1a1a1a] @md:px-12"
    >
      <header className="border-b-2 border-[#1a1a1a] pb-5 text-center">
        <p className="text-[34px] font-extrabold uppercase leading-none tracking-[0.18em]">Suno</p>
        <p className="mt-3 text-[13px] font-medium uppercase tracking-[0.14em] text-[#5c5c5c]">{hoje}</p>
      </header>

      <TituloHtml
        como="h2"
        html={estrutura.tituloHtml}
        atributos={estrutura.atributosDoTitulo}
        className="mt-9 text-[30px] font-bold leading-[1.15] tracking-[-0.01em] @md:text-[36px]"
      />
      {estrutura.lide && (
        <TrechoHtml blocos={[estrutura.lide]} className="mt-5 [--corpo-cor:#3a3a3a] [--corpo-tamanho:19px]" />
      )}

      {topicos.length > 0 && (
        <aside aria-label="Em resumo" className="mt-8 rounded-lg bg-[#efece3] px-6 py-5">
          <h3 className="text-[12px] font-bold uppercase tracking-[0.12em]">Em resumo</h3>
          <ul className="mt-3 flex flex-col gap-2.5">
            {topicos.map((topico, indice) => (
              <li key={indice} className="flex gap-3 text-[15px] leading-snug">
                <span aria-hidden="true" className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-[#1a1a1a]" />
                <span className="line-clamp-2">{topico}</span>
              </li>
            ))}
          </ul>
        </aside>
      )}

      {estrutura.secoes.map((secao, indice) => (
        <section key={indice} className="mt-10 border-t border-[#d6d2c6] pt-7">
          <p className="text-[12px] font-bold tracking-[0.14em] text-[#6b6b6b]">{String(indice + 1).padStart(2, "0")}</p>
          {secao.titulo && (
            <TituloHtml
              como="h3"
              html={secao.tituloHtml}
              atributos={secao.atributosDoTitulo}
              className="mb-3 mt-1 text-[23px] font-bold leading-snug"
            />
          )}
          <TrechoHtml blocos={secao.blocos} />
        </section>
      ))}
    </article>
  );
}
