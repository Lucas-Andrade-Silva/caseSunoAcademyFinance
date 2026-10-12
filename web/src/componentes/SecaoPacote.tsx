// O Pacote de publicação da Célula: imagens, vídeo, legenda, hashtags e a conferência visual.
// Aprovar o Pacote (H5) é uma decisão à parte de aprovar o conteúdo. "Montar Pacotes" roda em
// segundo plano no servidor (renderiza as imagens) para esta Célula; o vídeo do Roteiro
// continua saindo pelo terminal (ADR 0004).
import { useEffect, useState } from "react";
import {
  aprovarPacote,
  montarPacotes,
  obterMontagem,
  urlDoArquivo,
  urlDoZipDoPacote,
  type Audiencia,
  type Formato,
  type PacotePublicacao,
} from "../dados/cliente";
import { mensagemDeFalha } from "../dados/cliente";
import {
  itensDaDistribuicao,
  rotuloDaComposicao,
} from "../lib/pacote";
import Chip from "./Chip";
import VisualizadorDeImagens from "./VisualizadorDeImagens";

export default function SecaoPacote({
  identificador,
  audiencia,
  formato,
  pacote,
  motivoSemPacote,
  onAtualizado,
  gatilhoDeMontagem = 0,
}: {
  identificador: string;
  audiencia: Audiencia;
  formato: Formato;
  pacote: PacotePublicacao | null;
  /** Por que esta Célula não pode ter Pacote agora; `null` quando pode ser montado. */
  motivoSemPacote: string | null;
  onAtualizado: () => void;
  /** Cada incremento inicia a montagem (aprovar e gerar carrossel). */
  gatilhoDeMontagem?: number;
}) {
  const [enviando, definirEnviando] = useState(false);
  const [erro, definirErro] = useState<string | null>(null);
  const [montando, definirMontando] = useState(false);
  const [aberta, definirAberta] = useState<number | null>(null);
  const [copiado, definirCopiado] = useState(false);
  const [revisor, definirRevisor] = useState("");
  const [observacao, definirObservacao] = useState("");

  // Enquanto o servidor monta, consulta o estado; ao terminar, recarrega os Pacotes.
  useEffect(() => {
    if (!montando) return;
    let ativo = true;
    const temporizador = window.setInterval(() => {
      obterMontagem(identificador)
        .then((estado) => {
          if (!ativo || estado.estado === "rodando") return;
          definirMontando(false);
          if (estado.estado === "erro")
            definirErro(`A montagem falhou: ${estado.mensagem}`);
          else onAtualizado();
        })
        .catch((falha: unknown) => {
          if (!ativo) return;
          definirMontando(false);
          definirErro(mensagemDeFalha(falha));
        });
    }, 1500);
    return () => {
      ativo = false;
      window.clearInterval(temporizador);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [montando, identificador]);

  useEffect(() => {
    if (gatilhoDeMontagem > 0 && motivoSemPacote === null) montar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gatilhoDeMontagem]);

  function montar() {
    definirErro(null);
    definirMontando(true);
    montarPacotes(identificador, audiencia, formato).catch((falha: unknown) => {
      definirMontando(false);
      definirErro(mensagemDeFalha(falha));
    });
  }

  if (pacote === null) {
    return (
      <section className="rounded-2xl bg-cartao p-3.5">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-[12.5px] font-bold">Pacote de publicação</h2>
          <span className="text-xs text-suave">
            vídeo · legenda · hashtags · imagens
          </span>
          <Chip>{montando ? "montando…" : "não montado"}</Chip>
          <div className="flex-1" />
          {motivoSemPacote === null && (
            <button
              type="button"
              disabled={montando}
              onClick={montar}
              className="rounded-full border border-[#55555b] px-3.5 py-1 text-xs font-semibold disabled:opacity-50"
            >
              {montando ? "Montando…" : "Montar pacote desta Célula"}
            </button>
          )}
        </div>
        <p className="mt-2 text-xs text-suave">
          {motivoSemPacote ??
            "Monta apenas o Pacote desta Célula: imagens, legenda e hashtags."}
        </p>
        {erro && (
          <p role="alert" className="mt-2 text-xs text-[#ffb3ad]">
            {erro}
          </p>
        )}
      </section>
    );
  }

  const defeitos = (pacote.conferencia?.medicoes ?? []).filter(
    (medicao) => medicao.defeito !== null && medicao.defeito !== undefined,
  );

  function aprovar() {
    definirEnviando(true);
    definirErro(null);
    aprovarPacote(identificador, audiencia, formato, {
      revisor: revisor.trim() || undefined,
      observacao: observacao.trim() || undefined,
    })
      .then(onAtualizado)
      .catch((falha: unknown) => {
        definirErro(mensagemDeFalha(falha));
      })
      .finally(() => definirEnviando(false));
  }

  const total = pacote.imagens?.length ?? 0;
  const direcaoDeArte = pacote.direcao_de_arte;
  const distribuicao = itensDaDistribuicao(direcaoDeArte?.distribuicao);
  const imagens = (pacote.imagens ?? []).map((imagem) => ({
    url: urlDoArquivo(pacote.execucao, imagem.caminho),
    rotulo: `Slide ${imagem.indice + 1} de ${total}`,
    nomeDoArquivo: `suno-${audiencia}-slide-${String(imagem.indice + 1).padStart(2, "0")}.png`,
  }));
  const textoParaCopiar = `${pacote.legenda}\n\n${(pacote.hashtags ?? []).join(" ")}`;

  function copiarLegenda() {
    navigator.clipboard
      .writeText(textoParaCopiar)
      .then(() => {
        definirCopiado(true);
        window.setTimeout(() => definirCopiado(false), 2000);
      })
      .catch(() =>
        definirErro(
          "Não foi possível copiar: selecione o texto e copie à mão.",
        ),
      );
  }

  return (
    <section className="rounded-2xl bg-cartao p-3.5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-[12.5px] font-bold">Pacote de publicação</h2>
        <Chip tom={pacote.aprovado_por_humano ? "ok" : "alerta"}>
          {pacote.aprovado_por_humano
            ? "aprovado (H5)"
            : "aguardando aprovação (H5)"}
        </Chip>
        {montando && <Chip>gerando o carrossel…</Chip>}
        <div className="flex-1" />
        <a
          href={urlDoZipDoPacote(identificador, audiencia, formato)}
          download
          className="rounded-full bg-suno px-3.5 py-1 text-xs font-bold text-white"
        >
          Baixar pacote (.zip)
        </a>
        {!pacote.aprovado_por_humano && (
          <button
            type="button"
            disabled={enviando}
            onClick={aprovar}
            className="rounded-full border border-[#55555b] px-3.5 py-1 text-xs font-semibold disabled:opacity-50"
          >
            Aprovar Pacote
          </button>
        )}
      </div>
      {erro && <p className="mt-2 text-xs text-[#ffb3ad]">{erro}</p>}

      {!pacote.aprovado_por_humano && (
        <div className="mt-3 grid gap-2 rounded-xl border border-linha bg-cartao-2 p-3 sm:grid-cols-[180px_1fr]">
          <label className="grid gap-1 text-[10.5px] text-suave">
            Revisor (opcional)
            <input
              value={revisor}
              onChange={(evento) => definirRevisor(evento.target.value)}
              maxLength={100}
              placeholder="Nome ou equipe"
              className="rounded-lg border border-linha bg-fundo px-2.5 py-1.5 text-xs text-texto"
            />
          </label>
          <label className="grid gap-1 text-[10.5px] text-suave">
            Observação da aprovação (opcional)
            <input
              value={observacao}
              onChange={(evento) => definirObservacao(evento.target.value)}
              maxLength={500}
              placeholder="O que ficou especialmente bom ou deve ser mantido"
              className="rounded-lg border border-linha bg-fundo px-2.5 py-1.5 text-xs text-texto"
            />
          </label>
          <p className="text-[10px] text-suave sm:col-span-2">
            Aprovar confirma que este Pacote será usado e vira um sinal positivo para futuras decisões visuais.
          </p>
        </div>
      )}

      {pacote.feedback_visual_humano && (
        <p className="mt-2 text-xs text-suave">
          Aprovação humana registrada
          {pacote.feedback_visual_humano.revisor
            ? ` por ${pacote.feedback_visual_humano.revisor}`
            : ""}
          {pacote.feedback_visual_humano.observacao
            ? ` — ${pacote.feedback_visual_humano.observacao}`
            : ""}
        </p>
      )}

      {imagens.length > 0 && (
        <>
          <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-6">
            {imagens.map((imagem, i) => (
              <button
                key={imagem.url}
                type="button"
                onClick={() => definirAberta(i)}
                aria-label={`Ampliar ${imagem.rotulo}`}
                className="group relative overflow-hidden rounded-md border border-linha hover:border-suno"
              >
                <img src={imagem.url} alt={imagem.rotulo} className="w-full" />
                <span className="absolute inset-x-0 bottom-0 bg-black/60 py-0.5 text-center text-[10px] opacity-0 transition group-hover:opacity-100">
                  Ampliar
                </span>
              </button>
            ))}
          </div>
          <p className="mt-1.5 text-[11px] text-suave">
            Clique em um slide para ampliar. Cada um tem 1080 × 1350 px, o
            formato 4:5 do feed.
          </p>
        </>
      )}
      {aberta !== null && (
        <VisualizadorDeImagens
          imagens={imagens}
          indice={aberta}
          onMudar={definirAberta}
          onFechar={() => definirAberta(null)}
        />
      )}

      {direcaoDeArte && (
        <div className="mt-3 rounded-xl border border-linha bg-cartao-2 p-3">
          <div className="flex flex-wrap items-center gap-2">
            <b className="text-[10.5px] uppercase tracking-wider text-suave">
              Direção de arte
            </b>
            <Chip>
              {direcaoDeArte.origem_do_plano === "ia"
                ? "Diretor IA"
                : "Regras locais"}
            </Chip>
            {distribuicao.map((item) => (
              <Chip key={item.composicao}>
                {item.rotulo} · {item.total}
              </Chip>
            ))}
            <span className="text-[11px] text-suave">
              {direcaoDeArte.repeticoes_consecutivas === 0
                ? "sem repetição consecutiva"
                : `${direcaoDeArte.repeticoes_consecutivas} repetição(ões) consecutiva(s)`}
            </span>
          </div>
          <ol className="mt-2 grid gap-1.5 sm:grid-cols-2">
            {(direcaoDeArte.escolhas ?? []).map((escolha) => (
              <li
                key={escolha.indice}
                className="rounded-lg border border-linha px-2.5 py-2 text-xs"
              >
                <b>
                  Slide {escolha.indice + 1} ·{" "}
                  {rotuloDaComposicao(escolha.composicao)}
                </b>
                <p className="mt-0.5 text-[11px] text-suave">
                  {(escolha.motivos ?? []).join(" · ") ||
                    "compatível com o conteúdo"}
                </p>
                <small className="mt-1 block text-[10px] uppercase tracking-wide text-suave">
                  intensidade {escolha.intensidade_visual ?? "media"}
                </small>
              </li>
            ))}
          </ol>
          {direcaoDeArte.origem_do_plano === "deterministico" &&
            direcaoDeArte.motivo_fallback && (
              <p className="mt-2 text-[10.5px] text-suave">
                Fallback automático: {direcaoDeArte.motivo_fallback}
              </p>
            )}
        </div>
      )}

      {pacote.video && (
        <video
          controls
          className="mt-3 max-h-96 rounded-md border border-linha"
          src={urlDoArquivo(pacote.execucao, pacote.video)}
        />
      )}

      {formato === "roteiro" && !pacote.video && (
        <p className="mt-3 text-xs text-suave">
          O vídeo do Roteiro sai pelo terminal, fora do grafo:{" "}
          <code className="rounded bg-cartao-2 px-1.5 py-0.5">
            uv run python -m suno.cli video --execucao {identificador}{" "}
            --audiencia {audiencia}
          </code>
        </p>
      )}

      <div className="mt-3 flex items-center gap-2">
        <b className="text-[10.5px] uppercase tracking-wider text-suave">
          Legenda
        </b>
        <button
          type="button"
          onClick={copiarLegenda}
          className="rounded-full border border-[#55555b] px-3 py-0.5 text-[11px] font-semibold hover:border-texto"
        >
          {copiado ? "Copiado ✓" : "Copiar legenda e hashtags"}
        </button>
      </div>
      <p className="mt-1.5 whitespace-pre-wrap text-sm">{pacote.legenda}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {(pacote.hashtags ?? []).map((hashtag) => (
          <span
            key={hashtag}
            className="rounded-full bg-cartao-2 px-2 py-0.5 text-xs text-suave"
          >
            {hashtag}
          </span>
        ))}
      </div>

      {defeitos.length > 0 ? (
        <ul className="mt-3 list-inside list-disc text-xs text-alerta">
          {defeitos.map((medicao, indice) => (
            <li key={indice}>
              {medicao.artefato}: {medicao.defeito}{" "}
              {medicao.detalhe && `— ${medicao.detalhe}`}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-suave">
          Nenhum defeito de render encontrado.
        </p>
      )}
      {pacote.conferencia?.juiz_visao && (
        <div className="mt-3 rounded-xl border border-linha bg-cartao-2 p-3 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <b>Eval visual</b>
            <Chip>{pacote.conferencia.juiz_visao.parece_quebrado ? "pede atenção" : "sem suspeita"}</Chip>
            <Chip>legibilidade · {pacote.conferencia.juiz_visao.legibilidade}</Chip>
            <Chip>coerência · {pacote.conferencia.juiz_visao.coerencia_visual}</Chip>
            <Chip>marca · {pacote.conferencia.juiz_visao.aderencia_marca}</Chip>
          </div>
          {(pacote.conferencia.juiz_visao.observacoes ?? []).length > 0 && (
            <ul className="mt-2 list-inside list-disc text-suave">
              {(pacote.conferencia.juiz_visao.observacoes ?? []).map((item, indice) => (
                <li key={indice}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      {!pacote.conferencia?.juiz_visao && pacote.conferencia?.mensagem_juiz_visao && (
        <p className="mt-2 text-xs text-suave">{pacote.conferencia.mensagem_juiz_visao}</p>
      )}
    </section>
  );
}
