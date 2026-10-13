// A janela dividida do editor de referência: ocupa a tela com 12 px de margem, metade esquerda
// escura com o conteúdo e metade direita livre (lá é uma foto; aqui, o que a janela mostra).
// Sai por um portal para fora das vistas, porque uma vista em transição tem `transform` e
// prenderia o `position: fixed`.
import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

interface Propriedades {
  esquerda: ReactNode;
  direita?: ReactNode;
  /** Mostra o "FECHAR" do canto e deixa o Esc fechar. Sem ele, só os botões da janela saem. */
  onFechar?: () => void;
  rotuloAcessivel: string;
}

export default function Modal({ esquerda, direita, onFechar, rotuloAcessivel }: Propriedades) {
  const raiz = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const anterior = document.activeElement as HTMLElement | null;
    raiz.current?.focus();
    return () => anterior?.focus?.();
  }, []);

  useEffect(() => {
    if (!onFechar) return;
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") onFechar();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [onFechar]);

  return createPortal(
    <div className="surge fixed inset-0 z-50 bg-black/70 p-3">
      <div
        ref={raiz}
        role="dialog"
        aria-modal="true"
        aria-label={rotuloAcessivel}
        tabIndex={-1}
        className="grid h-full overflow-hidden rounded-md border border-[#2f2f2f] bg-fundo outline-none lg:grid-cols-2"
      >
        <div className="relative flex min-h-0 flex-col overflow-y-auto px-6 pb-10 pt-[59px] sm:px-[88px]">
          {onFechar && (
            <button
              type="button"
              onClick={onFechar}
              className="absolute left-6 top-[52px] text-[12px] font-bold uppercase tracking-[0.04em] text-texto hover:text-mudo sm:left-[53px]"
            >
              Fechar
            </button>
          )}
          <div className={`flex min-h-0 flex-1 flex-col ${onFechar ? "mt-[72px]" : "mt-4"}`}>{esquerda}</div>
        </div>
        <div className="hidden min-h-0 overflow-y-auto bg-previa lg:block">{direita}</div>
      </div>
    </div>,
    document.body,
  );
}
