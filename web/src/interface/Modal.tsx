// A janela dividida do editor de referência: ocupa a tela com 12 px de margem, metade esquerda
// escura com o conteúdo e metade direita livre (lá é uma foto; aqui, o que a janela mostra).
// Sai por um portal para fora das vistas, porque uma vista em transição tem `transform` e
// prenderia o `position: fixed`.
import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

const abertas: HTMLDivElement[] = [];
let fundo: { elemento: HTMLElement; inert: string | null; oculto: string | null } | null = null;

function restaurarAtributo(elemento: HTMLElement, nome: string, valor: string | null) {
  if (valor === null) elemento.removeAttribute(nome);
  else elemento.setAttribute(nome, valor);
}

function focaveis(janela: HTMLElement): HTMLElement[] {
  return Array.from(janela.querySelectorAll<HTMLElement>(
    'button, a[href], input, select, textarea, [tabindex], [contenteditable="true"]',
  )).filter((elemento) => elemento.tabIndex >= 0
    && !elemento.matches(":disabled")
    && !elemento.closest("[inert]")
    && elemento.getClientRects().length > 0
    && getComputedStyle(elemento).visibility === "visible");
}

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
    const janela = raiz.current;
    if (!janela) return;
    const anterior = document.activeElement as HTMLElement | null;
    const abaixo = abertas.at(-1);
    if (abaixo) abaixo.inert = true;
    abertas.push(janela);
    janela.focus();
    if (!fundo) {
      const elemento = document.getElementById("raiz");
      if (elemento) {
        fundo = { elemento, inert: elemento.getAttribute("inert"), oculto: elemento.getAttribute("aria-hidden") };
        elemento.inert = true;
        elemento.setAttribute("aria-hidden", "true");
      }
    }
    const aoTabular = (evento: KeyboardEvent) => {
      if (abertas.at(-1) !== janela || evento.key !== "Tab") return;
      const elementos = focaveis(janela);
      const primeiro = elementos[0];
      const ultimo = elementos.at(-1);
      if (!primeiro || !ultimo) {
        evento.preventDefault();
        janela.focus();
      } else if (!elementos.includes(document.activeElement as HTMLElement)) {
        evento.preventDefault();
        (evento.shiftKey ? ultimo : primeiro).focus();
      } else if (evento.shiftKey && document.activeElement === primeiro) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault();
        primeiro.focus();
      }
    };
    const conterFoco = (evento: FocusEvent) => {
      if (abertas.at(-1) === janela && !janela.contains(evento.target as Node)) {
        (focaveis(janela)[0] ?? janela).focus();
      }
    };
    document.addEventListener("keydown", aoTabular);
    document.addEventListener("focusin", conterFoco);
    return () => {
      document.removeEventListener("keydown", aoTabular);
      document.removeEventListener("focusin", conterFoco);
      const eraSuperior = abertas.at(-1) === janela;
      abertas.splice(abertas.indexOf(janela), 1);
      const superior = abertas.at(-1);
      if (superior) superior.inert = false;
      else if (fundo) {
        restaurarAtributo(fundo.elemento, "inert", fundo.inert);
        restaurarAtributo(fundo.elemento, "aria-hidden", fundo.oculto);
        fundo = null;
      }
      if (eraSuperior) {
        if (anterior?.isConnected && !anterior.closest("[inert]")) anterior.focus();
        else superior?.focus();
      }
    };
  }, []);

  useEffect(() => {
    if (!onFechar) return;
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape" && abertas.at(-1) === raiz.current) {
        evento.preventDefault();
        onFechar();
      }
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
