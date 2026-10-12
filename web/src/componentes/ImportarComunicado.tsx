// "Importar documento": um PDF ou um texto vira uma Ata da Origem "Documentos importados".
// A rota recusa o que não for PDF nem texto UTF-8 e o que passar de 15 MB; a frase do servidor
// aparece no formulário.
import { useRef, useState, type FormEvent } from "react";
import { importarComunicado, type ResumoDaAta } from "../dados/cliente";
import { mensagemDeFalha } from "../dados/cliente";

const LIMITE_MB = 15;

export default function ImportarComunicado({
  onImportada,
}: {
  onImportada: (ata: ResumoDaAta) => void;
}) {
  const [aberto, definirAberto] = useState(false);
  const [titulo, definirTitulo] = useState("");
  const [data, definirData] = useState("");
  const [enviando, definirEnviando] = useState(false);
  const [erro, definirErro] = useState<string | null>(null);
  const campoDoArquivo = useRef<HTMLInputElement>(null);

  function fechar() {
    definirAberto(false);
    definirErro(null);
    definirTitulo("");
    definirData("");
  }

  function aoEscolherArquivo(arquivo: File | undefined) {
    if (arquivo && titulo.trim() === "") {
      definirTitulo(arquivo.name.replace(/\.[^.]+$/, ""));
    }
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    const arquivo = campoDoArquivo.current?.files?.[0];
    if (!arquivo) {
      definirErro("Escolha um arquivo PDF ou de texto.");
      return;
    }
    if (arquivo.size > LIMITE_MB * 1024 * 1024) {
      definirErro(`O arquivo passa de ${LIMITE_MB} MB.`);
      return;
    }
    definirEnviando(true);
    definirErro(null);
    importarComunicado(arquivo, titulo.trim(), data === "" ? null : data)
      .then((ata) => {
        onImportada(ata);
        fechar();
      })
      .catch((falha: unknown) => {
        definirErro(mensagemDeFalha(falha));
      })
      .finally(() => definirEnviando(false));
  }

  return (
    <div className="relative">
      <button
        type="button"
        aria-expanded={aberto}
        onClick={() => (aberto ? fechar() : definirAberto(true))}
        className="rounded-full border border-linha px-4 py-1.5 text-xs font-semibold hover:border-[#55555b]"
      >
        Importar documento
      </button>
      {aberto && (
        <form
          onSubmit={enviar}
          className="absolute right-0 z-20 mt-2 w-80 space-y-3 rounded-xl border border-linha bg-cartao-2 p-3.5 shadow-xl"
        >
          <div>
            <label
              htmlFor="arquivo-importado"
              className="mb-1 block text-[10.5px] font-bold uppercase tracking-wider text-suave"
            >
              Arquivo (PDF ou texto)
            </label>
            <input
              id="arquivo-importado"
              ref={campoDoArquivo}
              type="file"
              accept=".pdf,.txt,application/pdf,text/plain"
              onChange={(evento) => aoEscolherArquivo(evento.target.files?.[0])}
              className="block w-full text-xs text-suave file:mr-3 file:rounded-full file:border-0 file:bg-cartao file:px-3 file:py-1 file:text-xs file:text-texto"
            />
          </div>
          <div>
            <label
              htmlFor="titulo-importado"
              className="mb-1 block text-[10.5px] font-bold uppercase tracking-wider text-suave"
            >
              Título
            </label>
            <input
              id="titulo-importado"
              value={titulo}
              maxLength={200}
              onChange={(evento) => definirTitulo(evento.target.value)}
              className="w-full rounded-lg border border-linha bg-fundo px-2.5 py-1.5 text-sm"
            />
          </div>
          <div>
            <label
              htmlFor="data-importada"
              className="mb-1 block text-[10.5px] font-bold uppercase tracking-wider text-suave"
            >
              Data do documento (opcional)
            </label>
            <input
              id="data-importada"
              type="date"
              value={data}
              onChange={(evento) => definirData(evento.target.value)}
              className="w-full rounded-lg border border-linha bg-fundo px-2.5 py-1.5 text-sm"
            />
            <p className="mt-1 text-[11px] text-suave">Sem data, vale hoje.</p>
          </div>
          <p className="text-[11px] text-suave">
            O que entra aqui é <b className="text-texto">não calibrado</b>: Limiares e Léxico foram
            medidos só com Atas do Copom.
          </p>
          {erro && (
            <p role="alert" className="text-xs text-[#ffb3ad]">
              {erro}
            </p>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={enviando || titulo.trim() === ""}
              className="rounded-full bg-suno px-4 py-1.5 text-xs font-bold text-white disabled:opacity-50"
            >
              {enviando ? "Importando…" : "Importar"}
            </button>
            <button
              type="button"
              onClick={fechar}
              className="rounded-full border border-[#55555b] px-4 py-1.5 text-xs font-semibold"
            >
              Cancelar
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
