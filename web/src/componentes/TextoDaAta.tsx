// O texto integral de uma Ata, em leitura: capa, ficha da reunião, seções, parágrafos numerados
// justificados e notas. A estrutura vem de `lib/ata.ts`.
import { estruturarAta } from "../lib/ata";

const ROTULO_DA_FICHA =
  /^(Data:|Local:|Horários de início|Presentes:|Membros do Copom|Demais participantes)/;

export default function TextoDaAta({ texto }: { texto: string }) {
  const { capa, ficha, corpo, notas } = estruturarAta(texto);

  return (
    <article className="mx-auto max-w-[46rem] rounded-[13px] bg-cartao px-6 py-8 sm:px-12 sm:py-10">
      {capa.length > 0 && (
        <header className="mb-8 border-b border-linha pb-6 text-center">
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-suno">{capa[0]}</p>
          <h2 className="mt-2 text-[22px] font-bold leading-tight">{capa[1] ?? capa[0]}</h2>
          {capa.slice(2).map((linha) => (
            <p key={linha} className="mt-1 text-[13px] text-suave">
              {linha}
            </p>
          ))}
        </header>
      )}

      {ficha.length > 0 && (
        <section
          aria-label="Ficha da reunião"
          className="mb-8 rounded-xl border border-linha px-4 py-3 text-[12px] leading-relaxed text-suave"
        >
          {ficha.map((linha, i) => {
            const rotulo = ROTULO_DA_FICHA.exec(linha.trim())?.[0];
            return rotulo ? (
              <div key={i} className={i > 0 ? "mt-2" : ""}>
                <b className="text-texto">{rotulo}</b>
                {linha.trim().slice(rotulo.length)}
              </div>
            ) : (
              <div key={i}>{linha}</div>
            );
          })}
        </section>
      )}

      <div className="text-[15px] leading-[1.75]">
        {corpo.map((bloco, i) =>
          bloco.tipo === "tabela" ? (
            <figure key={i} className="my-7">
              <figcaption className="mb-2 text-[13px] leading-snug">
                <b>{bloco.legenda[0]}</b>
                {bloco.legenda.slice(1).map((l) => (
                  <span key={l} className="block text-suave">
                    {l}
                  </span>
                ))}
              </figcaption>
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-[13px] tabular-nums">
                  <thead>
                    <tr className="border-b border-linha text-suave">
                      {bloco.cabecalho.map((c, j) => (
                        <th key={j} className={`px-2 py-1.5 font-semibold ${j ? "text-right" : "text-left"}`}>
                          {c}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {bloco.linhas.map((linha, r) => (
                      <tr key={r} className="border-b border-linha/60">
                        {linha.map((c, j) => (
                          <td key={j} className={`px-2 py-1.5 ${j ? "text-right" : "text-left font-medium"}`}>
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
            <h3
              key={i}
              className="mb-3 mt-9 border-t border-linha pt-5 text-[17px] font-bold leading-snug"
            >
              {bloco.texto.replace(/(\p{L})(\d)$/u, "$1")}
              {/(\p{L})\d$/u.test(bloco.texto) && (
                <sup className="ml-0.5 text-[11px] text-suave">{bloco.texto.slice(-1)}</sup>
              )}
            </h3>
          ) : (
            <p
              key={i}
              lang="pt-BR"
              className={`mb-4 text-justify [hyphens:auto] ${bloco.numero ? "pl-8 -indent-8" : ""}`}
            >
              {bloco.numero && (
                <span className="inline-block w-8 font-bold tabular-nums text-suno">
                  {bloco.numero}.
                </span>
              )}
              {bloco.texto}
            </p>
          ),
        )}
      </div>

      {notas.length > 0 && (
        <footer className="mt-8 border-t border-linha pt-4 text-[12px] leading-relaxed text-suave">
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
