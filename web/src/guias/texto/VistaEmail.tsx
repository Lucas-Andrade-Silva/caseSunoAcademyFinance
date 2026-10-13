// O texto como e-mail aberto numa caixa de entrada: assunto, remetente "Suno", a coluna de 600 px
// sobre o fundo cinza e o rodapé de descadastro. Superfície clara dentro da área escura do app.
import type { EstruturaDoTexto } from "./estrutura";
import TrechoHtml, { TituloHtml } from "./TrechoHtml";

export default function VistaEmail({ estrutura, hoje }: { estrutura: EstruturaDoTexto; hoje: string }) {
  return (
    <article aria-label="E-mail" className="@container mx-auto w-full max-w-[780px] overflow-hidden rounded-xl bg-white text-[#1a1a1a]">
      <header className="border-b border-[#e6e6e6] px-5 pb-5 pt-6 @md:px-8">
        <TituloHtml
          como="h2"
          html={estrutura.tituloHtml}
          atributos={estrutura.atributosDoTitulo}
          className="text-[22px] font-semibold leading-snug"
        />
        <div className="mt-5 flex items-center gap-3">
          <span
            aria-hidden="true"
            className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[#1a1a1a] text-[16px] font-semibold text-white"
          >
            S
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[15px] font-semibold leading-tight">Suno</p>
            <p className="text-[13px] leading-tight text-[#5c5c5c]">para você</p>
          </div>
          <time className="hidden shrink-0 text-[13px] text-[#5c5c5c] @md:block">{hoje}</time>
        </div>
      </header>

      <div className="bg-[#f2f1ee] px-3 py-8 @md:px-6 @md:py-10">
        <div className="mx-auto w-full max-w-[600px] rounded-md bg-white px-6 py-9 @md:px-10">
          {estrutura.lide && <TrechoHtml blocos={[estrutura.lide]} className="mb-7 [--corpo-tamanho:18px]" />}
          {estrutura.secoes.map((secao, indice) => (
            <section key={indice} className={indice > 0 || estrutura.lide ? "mt-8" : ""}>
              {secao.titulo && (
                <TituloHtml
                  como="h3"
                  html={secao.tituloHtml}
                  atributos={secao.atributosDoTitulo}
                  className="mb-2 text-[19px] font-bold leading-snug"
                />
              )}
              <TrechoHtml blocos={secao.blocos} />
            </section>
          ))}
        </div>
        <p className="mx-auto mt-6 max-w-[600px] text-center text-[12px] leading-relaxed text-[#6b6b6b]">
          Você recebeu este e-mail da Suno. <span className="underline">Cancelar inscrição</span>
        </p>
      </div>
    </article>
  );
}
