// O texto como artigo de leitura longa: Lora, coluna estreita, assinatura com data e tempo de
// leitura, e uma frase do próprio texto em destaque depois da primeira seção.
import type { EstruturaDoTexto } from "./estrutura";
import TrechoHtml, { TituloHtml } from "./TrechoHtml";

export default function VistaArtigo({ estrutura, hoje }: { estrutura: EstruturaDoTexto; hoje: string }) {
  const comDestaque = estrutura.citacao !== null && estrutura.secoes.length >= 2;
  return (
    <article
      aria-label="Artigo"
      className="@container mx-auto w-full max-w-[800px] rounded-xl bg-[#fffdf9] px-6 py-12 text-[#1c1b19] @2xl:px-16 @2xl:py-16"
      style={{ fontFamily: "Lora Variable, Georgia, serif" }}
    >
      <TituloHtml
        como="h2"
        html={estrutura.tituloHtml}
        atributos={estrutura.atributosDoTitulo}
        className="text-[34px] font-semibold leading-[1.12] tracking-[-0.01em] @2xl:text-[46px]"
      />
      {estrutura.lide && (
        <TrechoHtml
          blocos={[estrutura.lide]}
          className="mt-6 [--corpo-cor:#4a4640] [--corpo-entrelinha:1.5] [--corpo-familia:Lora_Variable,Georgia,serif] [--corpo-tamanho:22px]"
        />
      )}
      <p className="mt-8 border-y border-[#e5e0d6] py-3 font-sans text-[14px] text-[#5f5a50]">
        Por <strong className="font-semibold text-[#1c1b19]">Suno</strong> · {hoje} · {estrutura.minutos} min de leitura
      </p>

      <div className="mt-10">
        {estrutura.secoes.map((secao, indice) => (
          <section key={indice} className={indice > 0 ? "mt-10" : ""}>
            {secao.titulo && (
              <TituloHtml
                como="h3"
                html={secao.tituloHtml}
                atributos={secao.atributosDoTitulo}
                className="mb-3 text-[27px] font-semibold leading-snug"
              />
            )}
            <TrechoHtml
              blocos={secao.blocos}
              className="[--corpo-entrelinha:1.8] [--corpo-espaco:1.2em] [--corpo-familia:Lora_Variable,Georgia,serif] [--corpo-tamanho:19px]"
            />
            {comDestaque && indice === 0 && (
              <figure className="my-12 border-y border-[#e5e0d6] py-9 text-center">
                <blockquote className="text-[26px] italic leading-[1.35] @2xl:text-[30px]">“{estrutura.citacao}”</blockquote>
              </figure>
            )}
          </section>
        ))}
      </div>
    </article>
  );
}
