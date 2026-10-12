// A guia Fontes ("/fontes"): um trilho horizontal por Origem, com os cartões de Ata, a bolinha
// de seleção que alimenta a Curadoria, **Importar documento** e **Atualizar fontes** (spec do
// front, seção 4.1, opção B). Atualizar precisa de rede e falha sem travar a tela.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { alterarOrigem, atualizarFontes, listarOrigens } from "../dados/cliente";
import { mensagemDeFalha } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { usarSelecaoDeAtas } from "../ganchos/SelecaoDeAtas";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import ImportarComunicado from "../componentes/ImportarComunicado";
import TrilhoDeOrigem from "../componentes/TrilhoDeOrigem";
import { podeUsarSelecao } from "../lib/fontes";
import { formatarDataCurta } from "../texto/rotulos";

const ATUALIZAR_A_CADA_MS = 2000;

export default function Fontes() {
  const [recarga, recarregar] = useState(0);
  const [ocupado, definirOcupado] = useState(false);
  const [aviso, definirAviso] = useState<string | null>(null);
  const { selecao, alternar, conferir } = usarSelecaoDeAtas();

  // Enquanto "Atualizar fontes" roda no servidor, a tela se atualiza sozinha.
  const estado = usarRequisicao(listarOrigens, [recarga], {
    atualizarACada: (dados) =>
      dados.atualizacao.estado === "rodando" ? ATUALIZAR_A_CADA_MS : null,
  });

  useEffect(() => {
    if (estado.situacao !== "pronto") return;
    const existentes = new Set(estado.dados.origens.flatMap((o) => o.atas.map((a) => a.identificador)));
    conferir(existentes);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estado]);

  if (estado.situacao === "carregando") return <Carregando rotulo="Carregando Fontes…" />;
  if (estado.situacao === "erro") return <MensagemErro erro={estado.erro} />;

  const { origens, atualizacao } = estado.dados;
  const pode = podeUsarSelecao(selecao);
  const atualizando = atualizacao.estado === "rodando";

  function atualizar() {
    definirOcupado(true);
    definirAviso(null);
    atualizarFontes()
      .then(() => recarregar((atual) => atual + 1))
      .catch((falha: unknown) => definirAviso(mensagemDeFalha(falha)))
      .finally(() => definirOcupado(false));
  }

  function mudarOrigem(identificador: string, ativa: boolean) {
    definirOcupado(true);
    definirAviso(null);
    alterarOrigem(identificador, ativa)
      .then(() => recarregar((atual) => atual + 1))
      .catch((falha: unknown) => definirAviso(mensagemDeFalha(falha)))
      .finally(() => definirOcupado(false));
  }

  return (
    <div className="px-5 py-4">
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-[17px] font-bold">Fontes</h1>
        {atualizacao.concluida_em && (
          <small className="text-xs text-suave">
            atualizado {formatarDataCurta(atualizacao.concluida_em)}
          </small>
        )}
        <div className="flex-1" />
        <ImportarComunicado onImportada={() => recarregar((atual) => atual + 1)} />
        <button
          type="button"
          disabled={ocupado || atualizando}
          onClick={atualizar}
          className="rounded-full bg-suno px-4 py-1.5 text-xs font-bold uppercase tracking-wide text-white disabled:opacity-50"
        >
          {atualizando ? "Atualizando…" : "Atualizar fontes"}
        </button>
      </div>

      {atualizacao.estado === "erro" && (
        <p
          role="alert"
          className="mb-4 rounded-xl border border-suno/45 bg-suno/10 px-3 py-2 text-sm text-[#ffb3ad]"
        >
          A atualização não terminou limpa: {atualizacao.mensagem}. O que já estava em disco foi
          mantido.
        </p>
      )}
      {atualizacao.estado === "ok" && atualizacao.mensagem && (
        <p className="mb-4 rounded-xl border border-ok/40 bg-ok/10 px-3 py-2 text-sm">
          {atualizacao.mensagem}
        </p>
      )}
      {aviso && (
        <p role="alert" className="mb-4 text-sm text-[#ffb3ad]">
          {aviso}
        </p>
      )}

      {origens.map((origem) => (
        <TrilhoDeOrigem
          key={origem.id}
          origem={origem}
          selecao={selecao}
          onAlternarSelecao={alternar}
          onAlternarOrigem={(ativa) => mudarOrigem(origem.id, ativa)}
          ocupado={ocupado}
        />
      ))}

      <div className="sticky bottom-0 -mx-5 mt-2 flex flex-wrap items-center gap-3 border-t border-linha bg-fundo/95 px-5 py-3">
        <span className="text-xs text-suave">
          {selecao.length === 0
            ? "Marque a bolinha de um cartão para prosseguir."
            : (pode.motivo ??
              `${selecao.length} ${selecao.length === 1 ? "item selecionado" : "itens selecionados"}.`)}
        </span>
        <div className="flex-1" />
        {pode.ok ? (
          <Link
            to="/curadoria"
            className="rounded-full bg-suno px-5 py-2 text-xs font-bold uppercase tracking-wide text-white"
          >
            Prosseguir
          </Link>
        ) : (
          <span className="cursor-not-allowed rounded-full bg-suno px-5 py-2 text-xs font-bold uppercase tracking-wide text-white opacity-40">
            Prosseguir
          </span>
        )}
      </div>
    </div>
  );
}
