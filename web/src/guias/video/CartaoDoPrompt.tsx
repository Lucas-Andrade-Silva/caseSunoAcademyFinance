// O cartão do prompt: o texto pronto para colar e o botão de copiar, que confirma com "Copiado".
// O texto rola dentro do cartão quando é longo, e continua selecionável se a cópia falhar.
import { useEffect, useState } from "react";
import Botao from "../../interface/Botao";
import { IconeCopiar, IconeMarca } from "../../interface/Icones";

type Estado = "parado" | "copiado" | "falhou";

const VOLTA_AO_NORMAL_MS = 2000;

export default function CartaoDoPrompt({ texto }: { texto: string }) {
  const [estado, definirEstado] = useState<Estado>("parado");

  useEffect(() => {
    if (estado === "parado") return;
    const temporizador = window.setTimeout(() => definirEstado("parado"), VOLTA_AO_NORMAL_MS);
    return () => window.clearTimeout(temporizador);
  }, [estado]);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      definirEstado("copiado");
    } catch {
      definirEstado("falhou");
    }
  }

  return (
    <section aria-label="Prompt" className="rounded-xl bg-superficie">
      <header className="flex items-center justify-between gap-4 px-7 pb-4 pt-6">
        <h2 className="text-[17px]">Prompt</h2>
        <Botao
          variante="claro"
          tamanho="pequeno"
          onClick={() => void copiar()}
          icone={estado === "copiado" ? <IconeMarca size={16} strokeWidth={2.5} /> : <IconeCopiar size={16} />}
        >
          {estado === "copiado" ? "Copiado" : "Copiar"}
        </Botao>
      </header>
      {estado === "falhou" && (
        <p role="alert" className="px-7 pb-3 text-[14px] leading-snug text-coral-claro">
          Não consegui copiar. Selecione o texto.
        </p>
      )}
      <div
        tabIndex={0}
        role="region"
        aria-label="Texto do prompt"
        className="max-h-[420px] overflow-y-auto overscroll-contain whitespace-pre-wrap px-7 pb-7 text-[14px] leading-[1.65] text-claro"
      >
        {texto}
      </div>
      <span role="status" className="sr-only">
        {estado === "copiado" ? "Prompt copiado" : ""}
      </span>
    </section>
  );
}
