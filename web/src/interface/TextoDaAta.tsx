// O texto de uma notícia já estruturado: capa, ficha da reunião, seções, parágrafos numerados,
// tabelas e notas. A estrutura vem de `lib/ata.ts`; o texto de origem nunca é alterado.
import { estruturarAta } from "../lib/ata";

const ROTULO_DA_FICHA =
  /^(Data:|Local:|Horários de início|Presentes:|Membros do Copom|Demais participantes)/;

export default function TextoDaAta({ texto }: { texto: string }) {
  const { capa, ficha, corpo, notas } = estruturarAta(texto);

  return (
    <article className="rounded-xl bg-superficie px-6 py-8 sm:px-10 sm:py-10">
      {capa.length > 0 && (
        <header className="mb-8 border-b border-[#3a3a3a] pb-6">
          <p className="text-[12px] font-medium uppercase tracking-[0.04em] text-etiqueta">{capa[0]}</p>
          <h2 className="mt-2 text-[24px] font-normal leading-tight">{capa[1] ?? capa[0]}</h2>
          {capa.slice(2).map((linha) => (
            <p key={linha} className="mt-1 text-[14px] text-etiqueta">
              {linha}
            </p>
          ))}
        </header>
      )}

      {ficha.length > 0 && (
        <section
          aria-label="Ficha da reunião"
          className="mb-8 rounded-lg bg-fundo px-5 py-4 text-[14px] leading-relaxed text-etiqueta"
        >
          {ficha.map((linha, i) => {
            const rotulo = ROTULO_DA_FICHA.exec(linha.trim())?.[0];
            return rotulo ? (
              <div key={i} className={i > 0 ? "mt-2" : ""}>
                <b className="font-semibold text-claro">{rotulo}</b>
                {linha.trim().slice(rotulo.length)}
              </div>
            ) : (
              <div key={i}>{linha}</div>
            );
          })}
        </section>
      )}

      <div className="text-[16px] leading-[1.75] text-claro">
        {corpo.map((bloco, i) =>
          bloco.tipo === "tabela" ? (
            <figure key={i} className="my-7">
              <figcaption className="mb-2 text-[14px] leading-snug">
                <b className="font-semibold">{bloco.legenda[0]}</b>
                {bloco.legenda.slice(1).map((l) => (
                  <span key={l} className="block text-etiqueta">
                    {l}
                  </span>
                ))}
              </figcaption>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-[14px] tabular-nums">
                  <thead>
                    <tr className="border-b border-[#3a3a3a] text-etiqueta">
                      {bloco.cabecalho.map((c, j) => (
                        <th key={j} className={`px-2 py-1.5 font-medium ${j ? "text-right" : "text-left"}`}>
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {bloco.linhas.map((linha, r) => (
                      <tr key={r} className="border-b border-[#333]">
                        {linha.map((c, j) => (
                          <td key={j} className={`px-2 py-1.5 ${j ? "text-right" : "text-left"}`}>
                            {c}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </figure>
          ) : bloco.tipo === "secao" ? (
            <h3 key={i} className="mb-3 mt-9 border-t border-[#3a3a3a] pt-5 text-[20px] font-normal leading-snug text-texto">
              {bloco.texto.replace(/(\p{L})(\d)$/u, "$1")}
              {/(\p{L})\d$/u.test(bloco.texto) && (
                <sup className="ml-0.5 text-[11px] text-etiqueta">{bloco.texto.slice(-1)}</sup>
              )}
            </h3>
          ) : (
            <p
              key={i}
              lang="pt-BR"
              className={`mb-4 text-justify [hyphens:auto] ${bloco.numero ? "-indent-8 pl-8" : ""}`}
            >
              {bloco.numero && (
                <span className="inline-block w-8 font-semibold tabular-nums text-etiqueta">{bloco.numero}.</span>
              )}
              {bloco.texto}
            </p>
          ),
        )}
      </div>

      {notas.length > 0 && (
        <footer className="mt-8 border-t border-[#3a3a3a] pt-4 text-[13px] leading-relaxed text-etiqueta">
          {notas.map((nota, i) => (
            <p key={i} className="mb-1 text-justify">
              {nota}
            </p>
          ))}
        </footer>
      )}
    </article>
  );
}
