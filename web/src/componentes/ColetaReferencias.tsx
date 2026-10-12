import { useState, type FormEvent } from "react";
import {
  adicionarPerfilDeReferencia,
  coletarReferencias,
  descobrirReferencias,
  listarPerfisDeReferencia,
  mensagemDeFalha,
  type SetorDaReferencia,
} from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";

const SETORES: Array<{ valor: SetorDaReferencia | ""; rotulo: string }> = [
  { valor: "", rotulo: "Todos os setores" },
  { valor: "investimentos", rotulo: "Investimentos" },
  { valor: "financas_pessoais", rotulo: "Finanças pessoais" },
  { valor: "economia", rotulo: "Economia" },
  { valor: "mercado_financeiro", rotulo: "Mercado financeiro" },
  { valor: "criptoativos", rotulo: "Criptoativos" },
  { valor: "outros", rotulo: "Outros" },
];

export default function ColetaReferencias() {
  const [recarga, definirRecarga] = useState(0);
  const [ocupado, definirOcupado] = useState<string | null>(null);
  const [aviso, definirAviso] = useState<string | null>(null);
  const [janela, definirJanela] = useState(30);
  const [setor, definirSetor] = useState<SetorDaReferencia | "">("");
  const estado = usarRequisicao(
    async () => ({
      perfis: await listarPerfisDeReferencia(),
      descoberta: await descobrirReferencias(janela, setor || null),
    }),
    [recarga, janela, setor],
  );

  function cadastrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const formulario = evento.currentTarget;
    const usuario = String(new FormData(formulario).get("usuario") ?? "");
    definirOcupado("perfil");
    definirAviso(null);
    adicionarPerfilDeReferencia(usuario)
      .then(() => {
        formulario.reset();
        definirRecarga((valor) => valor + 1);
      })
      .catch((erro: unknown) => definirAviso(mensagemDeFalha(erro)))
      .finally(() => definirOcupado(null));
  }

  function coletar() {
    definirOcupado("coleta");
    definirAviso(null);
    coletarReferencias(janela)
      .then((resultado) => {
        const resumo = `${resultado.candidatos_novos} candidato(s) novo(s).`;
        const falhas = resultado.falhas ?? [];
        definirAviso(
          falhas.length
            ? `${resumo} ${falhas.join(" ")}`
            : resumo,
        );
        definirRecarga((valor) => valor + 1);
      })
      .catch((erro: unknown) => definirAviso(mensagemDeFalha(erro)))
      .finally(() => definirOcupado(null));
  }

  const perfisEmAlta =
    estado.situacao === "pronto" ? (estado.dados.descoberta.perfis ?? []) : [];
  const candidatos =
    estado.situacao === "pronto" ? (estado.dados.descoberta.candidatos ?? []) : [];

  return (
    <section className="mb-5 rounded-xl border border-linha bg-cartao p-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[240px] flex-1">
          <h2 className="text-sm font-bold">Descoberta de referências</h2>
          <p className="mt-1 text-[11px] leading-relaxed text-suave">
            Compara a movimentação dos perfis públicos monitorados no período e setor
            escolhidos. A consulta não usa login e nunca aprova um exemplo automaticamente.
          </p>
        </div>
        <form onSubmit={cadastrar} className="flex gap-2">
          <input
            name="usuario"
            required
            placeholder="@perfil.publico"
            className="w-40 rounded-lg border border-linha bg-fundo px-3 py-1.5 text-xs"
          />
          <button
            disabled={ocupado !== null}
            className="rounded-full border border-[#55555b] px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
          >
            Adicionar perfil
          </button>
        </form>
        <select
          value={janela}
          onChange={(evento) => definirJanela(Number(evento.target.value))}
          className="rounded-lg border border-linha bg-fundo px-3 py-1.5 text-xs"
          aria-label="Janela da coleta"
        >
          {[30, 60, 90].map((dias) => (
            <option key={dias} value={dias}>{dias} dias</option>
          ))}
        </select>
        <select
          value={setor}
          onChange={(evento) => definirSetor(evento.target.value as SetorDaReferencia | "")}
          className="rounded-lg border border-linha bg-fundo px-3 py-1.5 text-xs"
          aria-label="Setor da descoberta"
        >
          {SETORES.map((opcao) => (
            <option key={opcao.valor || "todos"} value={opcao.valor}>{opcao.rotulo}</option>
          ))}
        </select>
        <button
          type="button"
          onClick={coletar}
          disabled={ocupado !== null || estado.situacao !== "pronto" || estado.dados.perfis.length === 0}
          className="rounded-full bg-suno px-4 py-1.5 text-xs font-bold text-white disabled:opacity-50"
        >
          {ocupado === "coleta" ? "Consultando…" : "Buscar carrosséis"}
        </button>
      </div>

      {aviso && (
        <p role="status" className="mt-3 rounded-lg bg-[#2f2f34] px-3 py-2 text-xs text-suave">
          {aviso}
        </p>
      )}

      {estado.situacao === "erro" && (
        <p role="alert" className="mt-3 text-xs text-[#ffb3ad]">{estado.erro.message}</p>
      )}
      {estado.situacao === "pronto" && (
        <>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {estado.dados.perfis.map((perfil) => (
              <span key={perfil.usuario} className="rounded-full border border-linha px-2.5 py-1 text-[10px] text-suave">
                @{perfil.usuario} · {perfil.ultimo_estado.replaceAll("_", " ")}
              </span>
            ))}
          </div>
          {perfisEmAlta.length > 0 && (
            <div className="mt-4">
              <h3 className="text-xs font-bold">Perfis com mais movimentação</h3>
              <div className="mt-2 flex flex-wrap gap-2">
                {perfisEmAlta.map((perfil, indice) => (
                  <div key={perfil.usuario} className="rounded-lg border border-linha bg-fundo px-3 py-2 text-[10px]">
                    <b className="text-texto">{indice + 1}. @{perfil.usuario}</b>
                    <span className="ml-2 text-suave">
                      {perfil.publicacoes} carrossel(is) · {perfil.movimentacao.toLocaleString("pt-BR")} interações
                      {perfil.taxa_engajamento_media == null
                        ? ""
                        : ` · ${perfil.taxa_engajamento_media.toLocaleString("pt-BR")}% aprox.`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {candidatos.length > 0 && (
            <div className="mt-4 grid gap-2 lg:grid-cols-2">
              {candidatos.map((candidato) => (
                <article key={candidato.identificador} className="rounded-lg border border-linha bg-fundo p-3">
                  <div className="flex items-start gap-3">
                    {candidato.capa_url && (
                      <img
                        src={candidato.capa_url}
                        alt="Capa pública do carrossel"
                        loading="lazy"
                        className="h-20 w-16 shrink-0 rounded-md border border-linha object-cover"
                      />
                    )}
                    <div className="min-w-0 flex-1">
                      <b className="line-clamp-2 text-xs">{candidato.titulo}</b>
                      <p className="mt-1 text-[10px] text-suave">
                        @{candidato.usuario} · {new Date(candidato.publicado_em).toLocaleDateString("pt-BR")}
                        {` · ${SETORES.find((item) => item.valor === candidato.setor)?.rotulo ?? candidato.setor}`}
                        {candidato.taxa_engajamento == null
                          ? ""
                          : ` · ${candidato.taxa_engajamento.toLocaleString("pt-BR")}% aprox.`}
                      </p>
                    </div>
                    <a href={candidato.url} target="_blank" rel="noreferrer" className="text-[10px] text-[#ffb3ad] hover:underline">
                      Ver carrossel
                    </a>
                  </div>
                </article>
              ))}
            </div>
          )}
          {estado.dados.perfis.length > 0 && candidatos.length === 0 && (
            <p className="mt-4 text-xs text-suave">
              Nenhum carrossel encontrado para este período e setor. Tente ampliar o filtro.
            </p>
          )}
        </>
      )}
    </section>
  );
}
