// "Importar documento": um PDF ou um texto vira uma Ata da Origem "Documentos importados". A
// rota recusa o que não for PDF nem texto UTF-8 e o que passar de 15 MB; a frase do servidor
// aparece na janela. À direita, o arquivo escolhido.
import { useRef, useState, type FormEvent } from "react";
import { importarComunicado, mensagemDeFalha, type ResumoDaAta } from "../../dados/cliente";
import Botao from "../../interface/Botao";
import { IconeArquivoMais, IconeEnviar, IconeGirando } from "../../interface/Icones";
import { Quadrado } from "../../interface/Linha";
import Modal from "../../interface/Modal";

const LIMITE_MB = 15;

function tamanhoLegivel(bytes: number): string {
  return bytes >= 1024 * 1024
    ? `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`
    : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

const CAMPO =
  "h-[56px] w-full rounded-lg bg-superficie px-5 text-[17px] text-texto outline-none placeholder:text-apagado focus:ring-1 focus:ring-claro/60";

export default function ImportarComunicado({
  onFechar,
  onImportada,
}: {
  onFechar: () => void;
  onImportada: (ata: ResumoDaAta) => void;
}) {
  const [arquivo, definirArquivo] = useState<File | null>(null);
  const [titulo, definirTitulo] = useState("");
  const [data, definirData] = useState("");
  const [enviando, definirEnviando] = useState(false);
  const [erro, definirErro] = useState<string | null>(null);
  const campoDoArquivo = useRef<HTMLInputElement>(null);

  function aoEscolher(escolhido: File | undefined) {
    if (!escolhido) return;
    definirArquivo(escolhido);
    definirErro(null);
    if (titulo.trim() === "") definirTitulo(escolhido.name.replace(/\.[^.]+$/, ""));
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault();
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
      .then(onImportada)
      .catch((falha: unknown) => definirErro(mensagemDeFalha(falha)))
      .finally(() => definirEnviando(false));
  }

  const esquerda = (
    <form onSubmit={enviar} className="flex max-w-[489px] flex-col">
      <h2 className="text-[30px] font-normal leading-[1.3]">Importar documento</h2>
      <p className="mt-3 text-[20px] leading-snug text-apagado">PDF ou texto, até {LIMITE_MB} MB.</p>

      <input
        ref={campoDoArquivo}
        type="file"
        accept=".pdf,.txt,.md,application/pdf,text/plain,text/markdown"
        className="sr-only"
        tabIndex={-1}
        onChange={(evento) => aoEscolher(evento.target.files?.[0])}
      />
      <div className="mt-10 flex flex-col gap-2.5">
        <button
          type="button"
          onClick={() => campoDoArquivo.current?.click()}
          className="flex h-[70px] w-full items-center gap-4 rounded-lg bg-superficie px-[21px] text-left transition-colors duration-150 hover:bg-superficie-alta"
        >
          <IconeEnviar size={26} className="text-claro" />
          <span className="flex-1 truncate text-[17px]">{arquivo ? arquivo.name : "Escolher arquivo"}</span>
        </button>
        <label className="sr-only" htmlFor="titulo-importado">
          Título
        </label>
        <input
          id="titulo-importado"
          value={titulo}
          onChange={(evento) => definirTitulo(evento.target.value)}
          placeholder="Título"
          className={CAMPO}
        />
        <label className="sr-only" htmlFor="data-importada">
          Data
        </label>
        <input
          id="data-importada"
          type="date"
          value={data}
          onChange={(evento) => definirData(evento.target.value)}
          className={`${CAMPO} [color-scheme:dark]`}
        />
      </div>

      {erro && (
        <p role="alert" className="mt-4 text-[14px] leading-snug text-coral-claro">
          {erro}
        </p>
      )}
      <div className="mt-6">
        <Botao
          type="submit"
          variante="claro"
          tamanho="grande"
          disabled={enviando || !arquivo}
          icone={enviando ? <IconeGirando className="animate-spin" size={20} /> : undefined}
        >
          {enviando ? "Importando" : "Importar"}
        </Botao>
      </div>
    </form>
  );

  const direita = (
    <div className="grid h-full min-h-[320px] place-items-center p-[50px]">
      {arquivo ? (
        <div className="surge flex w-full max-w-[420px] items-center gap-4 rounded-xl bg-superficie p-5">
          <Quadrado cor="roxo" tamanho={48}>
            <IconeArquivoMais size={24} />
          </Quadrado>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-[17px]">{arquivo.name}</span>
            <span className="mt-0.5 block text-[13px] text-etiqueta">{tamanhoLegivel(arquivo.size)}</span>
          </span>
        </div>
      ) : (
        <IconeArquivoMais size={72} strokeWidth={1} className="text-[#2f2f2f]" />
      )}
    </div>
  );

  return <Modal rotuloAcessivel="Importar documento" esquerda={esquerda} direita={direita} onFechar={onFechar} />;
}
