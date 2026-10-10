// O Pacote de publicação da Célula: imagens, vídeo, legenda, hashtags e a conferência visual.
// Aprovar o Pacote (H5) é uma decisão à parte de aprovar o conteúdo. Ainda não há botão para
// montar o Pacote pela tela: ele sai pelo terminal.
import { useState } from "react";
import {
  aprovarPacote,
  urlDoArquivo,
  type Audiencia,
  type Formato,
  type PacotePublicacao,
} from "../dados/cliente";
import Chip from "./Chip";

export default function SecaoPacote({
  identificador,
  audiencia,
  formato,
  pacote,
  onAtualizado,
}: {
  identificador: string;
  audiencia: Audiencia;
  formato: Formato;
  pacote: PacotePublicacao | null;
  onAtualizado: () => void;
}) {
  const [enviando, definirEnviando] = useState(false);
  const [erro, definirErro] = useState<string | null>(null);

  if (pacote === null) {
    return (
      <section className="rounded-2xl bg-cartao p-3.5">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="text-[12.5px] font-bold">Pacote de publicação</h2>
          <span className="text-xs text-suave">vídeo · legenda · hashtags · imagens</span>
          <Chip>não montado</Chip>
        </div>
        <p className="mt-2 text-xs text-suave">
          Só Célula aprovada gera Pacote. Ele sai pelo terminal:{" "}
          <code className="rounded bg-cartao-2 px-1.5 py-0.5">
            uv run python -m suno.cli pacote --execucao {identificador}
          </code>
        </p>
      </section>
    );
  }

  const defeitos = (pacote.conferencia?.medicoes ?? []).filter(
    (medicao) => medicao.defeito !== null && medicao.defeito !== undefined,
  );

  function aprovar() {
    definirEnviando(true);
    definirErro(null);
    aprovarPacote(identificador, audiencia, formato)
      .then(onAtualizado)
      .catch((falha: unknown) => {
        definirErro(falha instanceof Error ? falha.message : String(falha));
      })
      .finally(() => definirEnviando(false));
  }

  return (
    <section className="rounded-2xl bg-cartao p-3.5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-[12.5px] font-bold">Pacote de publicação</h2>
        <Chip tom={pacote.aprovado_por_humano ? "ok" : "alerta"}>
          {pacote.aprovado_por_humano ? "aprovado (H5)" : "aguardando aprovação (H5)"}
        </Chip>
        <div className="flex-1" />
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

      {pacote.imagens && pacote.imagens.length > 0 && (
        <div className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-6">
          {pacote.imagens.map((imagem) => (
            <img
              key={imagem.indice}
              src={urlDoArquivo(pacote.execucao, imagem.caminho)}
              alt={`Slide ${imagem.indice + 1}`}
              className="rounded-md border border-linha"
            />
          ))}
        </div>
      )}

      {pacote.video && (
        <video
          controls
          className="mt-3 max-h-96 rounded-md border border-linha"
          src={urlDoArquivo(pacote.execucao, pacote.video)}
        />
      )}

      <p className="mt-3 whitespace-pre-wrap text-sm">{pacote.legenda}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {(pacote.hashtags ?? []).map((hashtag) => (
          <span key={hashtag} className="rounded-full bg-cartao-2 px-2 py-0.5 text-xs text-suave">
            {hashtag}
          </span>
        ))}
      </div>

      {defeitos.length > 0 ? (
        <ul className="mt-3 list-inside list-disc text-xs text-alerta">
          {defeitos.map((medicao, indice) => (
            <li key={indice}>
              {medicao.artefato}: {medicao.defeito} {medicao.detalhe && `— ${medicao.detalhe}`}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-suave">Nenhum defeito de render encontrado.</p>
      )}
      {pacote.conferencia?.juiz_visao && (
        <p className="mt-1 text-xs text-suave">
          Juiz de visão:{" "}
          {pacote.conferencia.juiz_visao.parece_quebrado ? "parece quebrado" : "sem suspeita"}
        </p>
      )}
    </section>
  );
}
