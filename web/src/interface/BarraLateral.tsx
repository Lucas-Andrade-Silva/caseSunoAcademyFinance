// A barra lateral arredondada do editor de referência: avatar no topo, os ícones das guias e a
// engrenagem embaixo. A barrinha branca da guia ativa desliza entre os ícones (`.indicador`).
// Um ponto no ícone avisa de geração em andamento (pulsando) ou pronta e ainda não vista.
// Abaixo de 1024 px a barra vira uma faixa na base da tela.
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { GUIAS, guiaDoCaminho, type Guia, type IdDaGuia } from "../nucleo/guias";
import { usarConfiguracoes } from "../nucleo/configuracoes";
import { usarSessoes } from "../nucleo/sessao";
import {
  IconeCarrossel,
  IconeConfiguracoes,
  IconeHistorico,
  IconeIngestao,
  IconePessoa,
  IconeTexto,
  IconeVideo,
} from "./Icones";

const ICONES: Record<IdDaGuia, ReactNode> = {
  ingestao: <IconeIngestao />,
  texto: <IconeTexto />,
  carrossel: <IconeCarrossel />,
  video: <IconeVideo />,
  historico: <IconeHistorico />,
  configuracoes: <IconeConfiguracoes size={26} />,
};

const DA_BARRA = GUIAS.filter((guia) => guia.id !== "configuracoes");
const DE_BAIXO = GUIAS.filter((guia) => guia.id === "configuracoes");

function Ponto({ estado }: { estado: "gerando" | "pronta" | null }) {
  if (!estado) return null;
  return (
    <span
      aria-hidden="true"
      className={`absolute right-3 top-3 h-2 w-2 rounded-full bg-white ${estado === "gerando" ? "pulsa" : ""}`}
    />
  );
}

function Botao({
  guia,
  ativa,
  ponto,
  referencia,
}: {
  guia: Guia;
  ativa: boolean;
  ponto: "gerando" | "pronta" | null;
  referencia: (elemento: HTMLAnchorElement | null) => void;
}) {
  return (
    <NavLink
      ref={referencia}
      to={guia.caminho}
      aria-label={guia.rotulo}
      className={`group relative grid h-[65px] w-full place-items-center transition-colors duration-200 max-lg:h-14 ${
        ativa ? "text-claro" : "text-mudo hover:text-claro"
      }`}
    >
      {ICONES[guia.id]}
      <Ponto estado={ponto} />
      <span
        role="tooltip"
        className="pointer-events-none absolute left-[calc(100%+14px)] top-1/2 z-40 -translate-y-1/2 whitespace-nowrap rounded-lg bg-ilha px-3.5 py-2 text-[13px] font-medium text-texto opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100 max-lg:hidden"
      >
        {guia.rotulo}
      </span>
    </NavLink>
  );
}

export default function BarraLateral() {
  const { pathname } = useLocation();
  const ativa = guiaDoCaminho(pathname);
  const sessoes = usarSessoes();
  const { nome } = usarConfiguracoes();
  const elementos = useRef(new Map<IdDaGuia, HTMLAnchorElement>());
  const raiz = useRef<HTMLElement>(null);
  const [posicao, definirPosicao] = useState<{ topo: number; esquerda: number; vertical: boolean } | null>(null);

  useLayoutEffect(() => {
    function medir() {
      const alvo = ativa ? elementos.current.get(ativa.id) : undefined;
      if (!alvo || !raiz.current) {
        definirPosicao(null);
        return;
      }
      // `offset*` não muda com o zoom da página, ao contrário de `getBoundingClientRect`.
      definirPosicao({
        topo: alvo.offsetTop + alvo.offsetHeight / 2 - 20,
        esquerda: alvo.offsetLeft + alvo.offsetWidth / 2 - 20,
        vertical: window.matchMedia("(min-width: 1024px)").matches,
      });
    }
    medir();
    window.addEventListener("resize", medir);
    return () => window.removeEventListener("resize", medir);
  }, [ativa]);

  function pontoDa(guia: Guia): "gerando" | "pronta" | null {
    if (!guia.formato) return null;
    const sessao = sessoes[guia.formato];
    if (sessao.fase === "enviando" || sessao.fase === "gerando") return "gerando";
    return sessao.naoVista ? "pronta" : null;
  }

  const inicial = nome.trim().charAt(0).toUpperCase();

  return (
    <nav
      ref={raiz}
      aria-label="Guias"
      className="fixed z-30 flex bg-superficie max-lg:inset-x-3 max-lg:bottom-3 max-lg:h-14 max-lg:flex-row max-lg:items-center max-lg:justify-around max-lg:rounded-[28px] lg:bottom-[30px] lg:left-[var(--rail-margem)] lg:top-[30px] lg:w-[var(--rail)] lg:flex-col lg:items-center lg:rounded-[35px]"
    >
      <span
        aria-hidden="true"
        className="mt-[18px] grid h-10 w-10 shrink-0 place-items-center rounded-full bg-claro text-[16px] font-semibold text-ilha max-lg:hidden"
      >
        {inicial || <IconePessoa size={20} />}
      </span>

      <div className="flex w-full flex-1 flex-col items-center justify-center pb-[12vh] max-lg:pb-0 max-lg:flex-row max-lg:justify-around max-lg:pt-0">
        {DA_BARRA.map((guia) => (
          <Botao
            key={guia.id}
            guia={guia}
            ativa={ativa?.id === guia.id}
            ponto={pontoDa(guia)}
            referencia={(elemento) => {
              if (elemento) elementos.current.set(guia.id, elemento);
              else elementos.current.delete(guia.id);
            }}
          />
        ))}
      </div>

      <div className="flex w-full flex-col items-center pb-3 max-lg:w-auto max-lg:pb-0">
        {DE_BAIXO.map((guia) => (
          <Botao
            key={guia.id}
            guia={guia}
            ativa={ativa?.id === guia.id}
            ponto={null}
            referencia={(elemento) => {
              if (elemento) elementos.current.set(guia.id, elemento);
              else elementos.current.delete(guia.id);
            }}
          />
        ))}
      </div>

      {posicao && (
        <span
          aria-hidden="true"
          className="indicador absolute left-0 top-0 h-10 w-[3px] rounded-r-full bg-claro max-lg:h-[3px] max-lg:w-10 max-lg:rounded-b-full max-lg:rounded-r-none"
          style={{
            transform: posicao.vertical
              ? `translateY(${posicao.topo}px)`
              : `translateX(${posicao.esquerda}px)`,
          }}
        />
      )}
    </nav>
  );
}
