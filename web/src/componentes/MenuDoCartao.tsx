// O menu "···" do cartão de uma Saída: renomear, exportar e excluir.
import { useState, type FormEvent } from "react";
import { excluirExecucao, renomearExecucao } from "../dados/cliente";
import { mensagemDeFalha } from "../dados/cliente";
import LinksDeExportacao from "./LinksDeExportacao";

export default function MenuDoCartao({
  identificador,
  nome,
  onRenomeada,
  onExcluida,
  completa = true,
}: {
  identificador: string;
  nome: string;
  onRenomeada: () => void;
  onExcluida: () => void;
  /** Sem `execucao.json` (na fila, falhou, interrompida) não há o que renomear nem exportar. */
  completa?: boolean;
}) {
  const [novoNome, definirNovoNome] = useState(nome);
  const [enviando, definirEnviando] = useState(false);
  const [erro, definirErro] = useState<string | null>(null);

  function salvar(evento: FormEvent) {
    evento.preventDefault();
    definirEnviando(true);
    definirErro(null);
    renomearExecucao(identificador, novoNome)
      .then(onRenomeada)
      .catch((falha: unknown) => {
        definirErro(mensagemDeFalha(falha));
      })
      .finally(() => definirEnviando(false));
  }

  function excluir() {
    if (
      !window.confirm(
        `Excluir "${nome}"? Isso apaga a Saída e seus arquivos do disco.`,
      )
    )
      return;
    definirEnviando(true);
    definirErro(null);
    excluirExecucao(identificador)
      .then(onExcluida)
      .catch((falha: unknown) => {
        definirErro(mensagemDeFalha(falha));
        definirEnviando(false);
      });
  }

  return (
    <details className="relative z-10">
      <summary
        aria-label="Mais ações"
        className="cursor-pointer list-none px-1 tracking-[2px] text-suave [&::-webkit-details-marker]:hidden"
      >
        ···
      </summary>
      <div className="absolute right-0 top-6 z-20 w-64 space-y-3 rounded-xl border border-linha bg-cartao-2 p-3 shadow-xl">
        {completa && (
          <form onSubmit={salvar} className="space-y-2">
            <label
              htmlFor={`nome-${identificador}`}
              className="block text-[10.5px] font-bold uppercase tracking-wider text-suave"
            >
              Renomear
            </label>
            <input
              id={`nome-${identificador}`}
              value={novoNome}
              onChange={(evento) => definirNovoNome(evento.target.value)}
              className="w-full rounded-lg border border-linha bg-fundo px-2.5 py-1.5 text-sm"
            />
            <button
              type="submit"
              disabled={enviando}
              className="rounded-full bg-suno px-3.5 py-1.5 text-xs font-bold text-white disabled:opacity-50"
            >
              Salvar nome
            </button>
            {erro && <p className="text-xs text-[#ffb3ad]">{erro}</p>}
          </form>
        )}
        {completa && (
          <div>
            <p className="mb-1 text-[10.5px] font-bold uppercase tracking-wider text-suave">
              Exportar
            </p>
            <LinksDeExportacao identificador={identificador} />
          </div>
        )}
        <div className={completa ? "border-t border-linha pt-3" : ""}>
          <button
            type="button"
            disabled={enviando}
            onClick={excluir}
            className="rounded-full border border-suno/60 px-3.5 py-1.5 text-xs font-bold text-[#ffb3ad] hover:bg-suno/10 disabled:opacity-50"
          >
            Excluir Saída
          </button>
          {!completa && erro && (
            <p className="mt-2 text-xs text-[#ffb3ad]">{erro}</p>
          )}
        </div>
      </div>
    </details>
  );
}
