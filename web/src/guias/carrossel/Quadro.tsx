// O quadro do carrossel desenhado em React com as medidas do render do servidor (1080 x 1350 px):
// formas orgânicas atrás, título dominante, painel de texto, número do quadro, marca "( SUNO )" e os
// pontos de paginação. As cores vêm da paleta, por variáveis CSS. É conteúdo, não interface: usa
// Anton e Poppins e a paleta escolhida, e a prévia só o escala. O mesmo componente, sem escala, é
// o que a exportação fotografa.
import { memo, useLayoutEffect, useRef, type CSSProperties, type ReactNode } from "react";
import "./quadro.css";
import { alturaDaBarra, partesDaComparacao } from "./graficos";
import { desenhoDoIcone } from "./icones";
import type { AncoraDeQuadro, Composicao, GraficoDoQuadro, IdDoIcone, Paleta, QuadroMontado } from "./modelo";
import { corSobre } from "./paletas";
import { garantirFontes } from "./tipografia";

/** O mesmo mínimo legível do servidor: o texto encolhe de 2 em 2 px até caber, e para aqui. */
const TAMANHO_MINIMO = 26;

function ajustar(caixa: HTMLElement): void {
  caixa.style.fontSize = "";
  let tamanho = parseFloat(getComputedStyle(caixa).fontSize);
  while (
    (caixa.scrollHeight > caixa.clientHeight + 1 || caixa.scrollWidth > caixa.clientWidth + 1) &&
    tamanho - 2 >= TAMANHO_MINIMO
  ) {
    tamanho -= 2;
    caixa.style.fontSize = `${tamanho}px`;
  }
}

function ajustarTudo(raiz: HTMLElement): void {
  raiz.querySelectorAll<HTMLElement>("[data-ajustar]").forEach(ajustar);
}

function variaveis(paleta: Paleta): CSSProperties {
  return {
    "--qd-fundo": paleta.fundo,
    "--qd-texto": paleta.texto,
    "--qd-destaque": paleta.destaque,
    "--qd-apoio": paleta.apoio,
    "--qd-sobre-destaque": corSobre(paleta.destaque, paleta.texto, paleta.fundo),
  } as CSSProperties;
}

function Titulo({ titulo, destaque }: { titulo: string; destaque?: string | null }) {
  const posicao = destaque ? titulo.indexOf(destaque) : -1;
  if (!destaque || posicao < 0) return <>{titulo}</>;
  return (
    <>
      {titulo.slice(0, posicao)}
      <span className="realce">{destaque}</span>
      {titulo.slice(posicao + destaque.length)}
    </>
  );
}

function Barra({ rotulo, ancora, cor, teto }: { rotulo: string; ancora: AncoraDeQuadro; cor: string; teto: number }) {
  return (
    <div className="barra">
      <div className="valor">{ancora.citacao}</div>
      <div className="bloco" style={{ height: alturaDaBarra(ancora.valor, teto, 260), background: cor }} />
      <div className="rotulo">{rotulo}</div>
    </div>
  );
}

function Grafico({ grafico }: { grafico: GraficoDoQuadro | null }) {
  if (!grafico) return null;
  if (grafico.jeito === "numero") {
    return (
      <div className="grafico">
        <div className="numero-grande">
          <div className="valor" data-ajustar>
            {grafico.ancora.citacao}
          </div>
          <div className="rotulo">{grafico.ancora.rotulo}</div>
        </div>
      </div>
    );
  }
  const teto = Math.max(grafico.antes.valor ?? 0, grafico.depois.valor ?? 0) || 1;
  return (
    <div className="grafico">
      <div className="barras">
        <Barra
          rotulo="Antes"
          ancora={grafico.antes}
          cor="color-mix(in srgb, var(--qd-texto) 45%, var(--qd-fundo))"
          teto={teto}
        />
        <Barra rotulo="Depois" ancora={grafico.depois} cor="var(--qd-destaque)" teto={teto} />
      </div>
    </div>
  );
}

function Icones({ ids }: { ids: readonly IdDoIcone[] }) {
  if (ids.length === 0) return null;
  const lado = ids.length <= 5 ? 76 : ids.length <= 8 ? 58 : 44;
  return (
    <div className="icones">
      {ids.map((id) => {
        const Desenho = desenhoDoIcone(id);
        return (
          <span key={id} style={{ width: lado, height: lado }}>
            <Desenho size={Math.round(lado * 0.56)} strokeWidth={2} />
          </span>
        );
      })}
    </div>
  );
}

function Linhas({ caminho, opacidade }: { caminho: string; opacidade: number }) {
  return (
    <svg className="linhas" viewBox="0 0 1080 520" fill="none" aria-hidden="true">
      <path d={caminho} style={{ stroke: "var(--qd-texto)" }} strokeOpacity={opacidade} strokeWidth="5" />
    </svg>
  );
}

const ARTE: Record<Composicao, ReactNode> = {
  editorial: (
    <>
      <div className="forma" style={{ width: 640, height: 760, right: -300, top: -260, borderRadius: "55% 45% 60% 40%" }} />
      <div className="forma escura" style={{ width: 720, height: 620, left: -350, bottom: -250, borderRadius: "42% 58% 38% 62%" }} />
      <div className="anel" style={{ width: 720, height: 720, right: -230, bottom: -160 }} />
    </>
  ),
  minimalista: (
    <>
      <div className="anel fraco" style={{ width: 980, height: 980, left: 50, top: 185 }} />
      <div className="brilho forma" style={{ width: 300, height: 300, right: -170, top: 90, opacity: 0.3 }} />
    </>
  ),
  infografico: (
    <>
      <div className="forma" style={{ width: 560, height: 520, right: -210, top: -210, borderRadius: "50% 50% 42% 58%" }} />
      <div className="forma escura" style={{ width: 620, height: 560, left: -300, bottom: -220, borderRadius: "58% 42% 55% 45%" }} />
      <Linhas caminho="M0 430 L140 390 L270 420 L420 310 L550 340 L700 220 L850 260 L1080 90" opacidade={0.22} />
    </>
  ),
  comparativo: (
    <>
      <div className="forma escura" style={{ width: 700, height: 650, left: -330, top: -260, borderRadius: "50%" }} />
      <div className="forma" style={{ width: 700, height: 650, right: -330, bottom: -260, borderRadius: "50%" }} />
      <div className="anel" style={{ width: 760, height: 760, left: 160, top: 330 }} />
    </>
  ),
  estatistico: (
    <>
      <div className="forma" style={{ width: 980, height: 880, left: 50, top: 260, borderRadius: "50%", opacity: 0.17 }} />
      <div className="anel forte" style={{ width: 720, height: 720, left: 180, top: 340 }} />
      <div className="anel" style={{ width: 560, height: 560, left: 260, top: 420 }} />
    </>
  ),
  narrativo: (
    <>
      <div className="forma" style={{ width: 660, height: 620, right: -260, top: -220, borderRadius: "55% 45% 60% 40%" }} />
      <div className="forma escura" style={{ width: 760, height: 620, left: -360, bottom: -260, borderRadius: "45% 55% 40% 60%" }} />
      <Linhas caminho="M0 420 L160 390 L300 320 L440 350 L590 240 L740 280 L900 150 L1080 110" opacidade={0.25} />
    </>
  ),
};

function Corpo({ quadro }: { quadro: QuadroMontado }) {
  const { slide, composicao, grafico, indice, total } = quadro;
  const titulo = (
    <div className="titulo" data-ajustar>
      <Titulo titulo={slide.titulo} destaque={slide.destaque} />
    </div>
  );
  const texto = (
    <div className="corpo" data-ajustar>
      {slide.corpo}
    </div>
  );
  switch (composicao) {
    case "minimalista":
      return (
        <>
          {titulo}
          <div className="regua" />
          {texto}
        </>
      );
    case "infografico":
      return (
        <>
          {titulo}
          <div className="painel acento">{texto}</div>
          <Grafico grafico={grafico} />
        </>
      );
    case "comparativo": {
      const [esquerda, direita] = partesDaComparacao(slide.corpo);
      return (
        <>
          {titulo}
          <div className="coluna a">
            <div className="rotulo-da-coluna">PONTO A</div>
            <div className="corpo" data-ajustar>
              {esquerda}
            </div>
          </div>
          <div className="coluna b">
            <div className="rotulo-da-coluna">PONTO B</div>
            <div className="corpo" data-ajustar>
              {direita}
            </div>
          </div>
          <Grafico grafico={grafico} />
        </>
      );
    }
    case "estatistico":
      return (
        <>
          {titulo}
          <Grafico grafico={grafico} />
          <div className="painel">{texto}</div>
        </>
      );
    case "narrativo":
      return (
        <>
          <div className="etapa">{indice + 1}</div>
          <div className="rotulo-da-etapa">
            ETAPA {indice + 1} DE {total}
          </div>
          {titulo}
          <div className="painel acento">{texto}</div>
        </>
      );
    default:
      return (
        <>
          {titulo}
          <div className="regua" />
          <div className="painel acento">{texto}</div>
        </>
      );
  }
}

interface Propriedades {
  quadro: QuadroMontado;
  paleta: Paleta;
  /** O selo do canto: a Audiência do carrossel. */
  selo: string;
}

function Quadro({ quadro, paleta, selo }: Propriedades) {
  const raiz = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const no = raiz.current;
    if (!no) return;
    ajustarTudo(no);
    let vivo = true;
    // As medidas só valem com as fontes carregadas; antes disso o navegador mede a reserva.
    void garantirFontes().then(() => {
      if (vivo) ajustarTudo(no);
    });
    return () => {
      vivo = false;
    };
  }, [quadro]);

  return (
    <div ref={raiz} className={`qd ${quadro.composicao}`} style={variaveis(paleta)} data-quadro={quadro.indice}>
      <div className="arte">{ARTE[quadro.composicao]}</div>
      <div className="topo">
        <div className="marca">
          <b>(</b> SUNO <b>)</b>
        </div>
        <div className="selo">{selo}</div>
      </div>
      <Corpo quadro={quadro} />
      <div className="pontos">
        {Array.from({ length: quadro.total }, (_, posicao) => (
          <i key={posicao} className={posicao === quadro.indice ? "ativo" : undefined} />
        ))}
      </div>
      <div className="numero">
        {quadro.indice + 1}/{quadro.total}
      </div>
      <Icones ids={quadro.icones} />
    </div>
  );
}

export default memo(Quadro);
