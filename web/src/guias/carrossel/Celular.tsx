// O celular da prévia: a tela de um feed (cabeçalho com o avatar "suno", o carrossel com setas e
// pontinhos de posição, curtir/comentar/compartilhar/guardar e a legenda). Cada quadro
// entra em 1080 x 1350 px e é escalado com `transform` para caber na tela; a troca desliza.
import { useRef, useState, type KeyboardEvent, type PointerEvent, type ReactNode } from "react";
import {
  IconeComentar,
  IconeCompartilhar,
  IconeCurtir,
  IconeGuardar,
  IconeReticencias,
  IconeSeta,
  IconeVoltarSeta,
} from "../../interface/Icones";
import { ALTURA_DO_QUADRO, LARGURA_DO_QUADRO } from "./modelo";

/** A tela por dentro da moldura de 7 px: 320 - 14. */
const LARGURA_DA_TELA = 306;
const ESCALA = LARGURA_DA_TELA / LARGURA_DO_QUADRO;
const ALTURA_DA_TELA = Math.round(ALTURA_DO_QUADRO * ESCALA);
const DISTANCIA_DO_DEDO = 40;

interface Propriedades {
  quadros: readonly ReactNode[];
  legenda: string;
  rotuloAcessivel: string;
}

function Seta({ lado, onClick }: { lado: "antes" | "depois"; onClick: () => void }) {
  const Icone = lado === "antes" ? IconeVoltarSeta : IconeSeta;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={lado === "antes" ? "Quadro anterior" : "Próximo quadro"}
      className={`absolute top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center rounded-full bg-black/60 text-white transition-colors duration-150 hover:bg-black/80 ${
        lado === "antes" ? "left-2" : "right-2"
      }`}
    >
      <Icone size={18} />
    </button>
  );
}

export default function Celular({ quadros, legenda, rotuloAcessivel }: Propriedades) {
  const [posicao, definirPosicao] = useState(0);
  const inicioDoToque = useRef<number | null>(null);
  const total = quadros.length;
  const atual = Math.min(posicao, Math.max(total - 1, 0));

  const ir = (indice: number) => definirPosicao(Math.min(Math.max(indice, 0), total - 1));

  function aoSoltar(evento: PointerEvent<HTMLDivElement>) {
    const inicio = inicioDoToque.current;
    inicioDoToque.current = null;
    if (inicio === null) return;
    const deslocamento = evento.clientX - inicio;
    if (Math.abs(deslocamento) >= DISTANCIA_DO_DEDO) ir(atual + (deslocamento < 0 ? 1 : -1));
  }

  function aoTeclar(evento: KeyboardEvent<HTMLDivElement>) {
    if (evento.key === "ArrowLeft") ir(atual - 1);
    if (evento.key === "ArrowRight") ir(atual + 1);
  }

  return (
    <div
      role="group"
      aria-roledescription="carrossel"
      aria-label={rotuloAcessivel}
      onKeyDown={aoTeclar}
      className="relative mx-auto flex h-[660px] w-[320px] shrink-0 flex-col overflow-hidden rounded-[46px] border-[7px] border-superficie bg-black text-white"
    >
      <span aria-hidden="true" className="mx-auto mt-2 h-[22px] w-[84px] shrink-0 rounded-full bg-fundo" />

      <header className="flex h-[46px] shrink-0 items-center gap-2.5 px-3">
        <span
          aria-hidden="true"
          className="grid h-[30px] w-[30px] place-items-center rounded-full bg-white text-[14px] font-bold text-ilha"
        >
          s
        </span>
        <span className="text-[13px] font-semibold">suno</span>
        <IconeReticencias size={20} className="ml-auto text-white" />
      </header>

      <div
        className="relative shrink-0 touch-pan-y select-none overflow-hidden"
        style={{ height: ALTURA_DA_TELA }}
        onPointerDown={(evento) => {
          inicioDoToque.current = evento.clientX;
        }}
        onPointerUp={aoSoltar}
        onPointerCancel={() => {
          inicioDoToque.current = null;
        }}
      >
        <div
          className="flex h-full transition-transform duration-[250ms] ease-[var(--ease-saida)] motion-reduce:transition-none"
          style={{ transform: `translateX(-${atual * 100}%)` }}
        >
          {quadros.map((quadro, indice) => (
            <div
              key={indice}
              className="relative h-full w-full shrink-0 overflow-hidden"
              aria-hidden={indice !== atual}
              inert={indice !== atual}
            >
              <div
                style={{
                  width: LARGURA_DO_QUADRO,
                  height: ALTURA_DO_QUADRO,
                  transform: `scale(${ESCALA})`,
                  transformOrigin: "top left",
                }}
              >
                {quadro}
              </div>
            </div>
          ))}
        </div>
        {atual > 0 && <Seta lado="antes" onClick={() => ir(atual - 1)} />}
        {atual < total - 1 && <Seta lado="depois" onClick={() => ir(atual + 1)} />}
      </div>

      <div className="relative flex h-11 shrink-0 items-center justify-between px-3">
        <span className="flex items-center gap-3.5">
          <IconeCurtir size={22} />
          <IconeComentar size={22} />
          <IconeCompartilhar size={22} />
        </span>
        {total > 1 && (
          <span aria-hidden="true" className="absolute left-1/2 flex -translate-x-1/2 items-center gap-1">
            {quadros.map((_, indice) => (
              <span
                key={indice}
                className={`h-1.5 w-1.5 rounded-full transition-colors duration-200 ${
                  indice === atual ? "bg-white" : "bg-[#555]"
                }`}
              />
            ))}
          </span>
        )}
        <IconeGuardar size={22} />
      </div>

      <p className="line-clamp-2 px-3 text-[12px] leading-snug">
        <b className="font-semibold">suno</b> {legenda}
      </p>
      <p className="mt-1.5 px-3 text-[12px] text-apagado">Ver todos os comentários</p>

      <span
        aria-hidden="true"
        className="absolute bottom-2 left-1/2 h-1 w-28 -translate-x-1/2 rounded-full bg-white/70"
      />
    </div>
  );
}
