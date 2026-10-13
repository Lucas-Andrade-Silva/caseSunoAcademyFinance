// O editor do carrossel, com o conteúdo já pronto. À esquerda: os quadros (texto e direção da imagem)
// e as configurações visuais (tipos, exemplos, paletas, ícones) com o botão Gerar carrossel. À direita:
// as barras do Laudo ou o celular de feed com o carrossel (ou com um exemplo), e embaixo Salvar no
// histórico e Exportar carrossel.
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import {
  AUDIENCIAS,
  listarReferenciasVisuais,
  obterAncorasDaCelula,
  urlDaImagemDaReferencia,
  type Audiencia,
  type Laudo,
  type Slide,
} from "../../dados/cliente";
import Barras from "../../interface/Barras";
import Botao from "../../interface/Botao";
import { CorpoDaPrevia, Divisao, Rotulo, Titulo, TituloDeSecao, TopoDaPrevia } from "../../interface/Divisao";
import { IconeBaixar, IconeGirando, IconeMarca, IconeSalvar } from "../../interface/Icones";
import { Pilulas } from "../../interface/Pilulas";
import Vazio from "../../interface/Vazio";
import { buscar, usarDados } from "../../nucleo/dados";
import { usarHistorico } from "../../nucleo/historico";
import { barrasDoLaudo } from "../../nucleo/laudo";
import { CHAVES } from "../../nucleo/precarga";
import { pluralizar, rotuloAudiencia } from "../../texto/rotulos";
import Celular from "./Celular";
import { COMPOSICAO_PADRAO, ehComposicao, rotuloDaComposicao } from "./composicoes";
import { dadosParaSalvar } from "./dadosSalvos";
import { mesmoDesign } from "./design";
import EscolhaDeComposicao from "./EscolhaDeComposicao";
import EscolhaDeExemplo from "./EscolhaDeExemplo";
import EscolhaDeIcones from "./EscolhaDeIcones";
import EscolhaDePaleta from "./EscolhaDePaleta";
import { baixarArquivo, fotografarQuadros, zipDosQuadros } from "./exportar";
import { ancoraDeQuadro } from "./graficos";
import type { AncoraDeQuadro, Composicao, Design, IdDoIcone, Montagem, Paleta, QuadroMontado } from "./modelo";
import { montarQuadros, quadrosDaMontagem, montarQuadrosDeExemplo } from "./montagem";
import { nomeDoZip } from "./nomesDeArquivo";
import { paletaPorId } from "./paletas";
import Quadro from "./Quadro";
import Quadros from "./Quadros";
import { garantirFontes } from "./tipografia";

type Vista = "avaliacao" | "previa";
type Mostrando = "gerado" | "exemplo";

/** O conteúdo de uma Audiência: os quadros, o Laudo e, num carrossel salvo, as Âncoras que já vieram. */
export interface OrigemDoEditor {
  audiencia: Audiencia;
  slides: Slide[];
  laudo: Laudo | null;
  ancoras?: AncoraDeQuadro[];
}

interface Propriedades {
  /** O nome que o Histórico dá ao salvo. */
  titulo: string;
  execucaoId: string | null;
  origens: readonly OrigemDoEditor[];
  /** Um carrossel salvo que a pessoa reabriu: entra já gerado, com as escolhas dele. */
  restaurado?: Montagem;
  design: Design | null;
  idDaPaleta: string;
  aoSalvarDesign: (design: Design) => void;
  aoEscolherPaleta: (id: string) => void;
  /** O ícone redondo ao lado do título: nova geração (sessão) ou sair do salvo. */
  acaoDoTitulo: { rotulo: string; icone: ReactNode; aoClicar: () => void };
}

const SEM_ANCORAS: AncoraDeQuadro[] = [];
const MOSTRA_O_FEITO_MS = 1800;

/** Um respiro para o React terminar de montar os quadros; temporizador, não quadro de animação, porque aba escondida não anima. */
function esperarMontagem(): Promise<void> {
  return new Promise((resolver) => window.setTimeout(resolver, 80));
}

function IlhaDaVista({
  vista,
  aoMudar,
}: {
  vista: Vista;
  aoMudar: (vista: Vista) => void;
}) {
  return (
    <span className="inline-flex h-[50px] items-center rounded-[25px] bg-ilha px-2">
      <Pilulas<Vista>
        rotuloAcessivel="O que mostrar"
        valor={vista}
        onMudar={aoMudar}
        opcoes={[
          { valor: "avaliacao", rotulo: "Avaliação" },
          { valor: "previa", rotulo: "Prévia" },
        ]}
      />
    </span>
  );
}

export default function Editor({
  titulo,
  execucaoId,
  origens,
  restaurado,
  design,
  idDaPaleta,
  aoSalvarDesign,
  aoEscolherPaleta,
  acaoDoTitulo,
}: Propriedades) {
  const { salvar } = usarHistorico();
  const { dados: referencias, erro: erroDasReferencias } = usarDados(CHAVES.referencias, listarReferenciasVisuais);

  const [audiencia, definirAudiencia] = useState<Audiencia>(restaurado?.audiencia ?? origens[0].audiencia);
  const origem = origens.find((o) => o.audiencia === audiencia) ?? origens[0];

  const [composicao, definirComposicao] = useState<Composicao>(
    restaurado?.composicao ?? design?.composicao ?? COMPOSICAO_PADRAO,
  );
  const [referenciaId, definirReferenciaId] = useState<string | null>(
    restaurado ? restaurado.referenciaId : (design?.referencia ?? null),
  );
  const [paleta, definirPaleta] = useState<Paleta>(restaurado?.paleta ?? paletaPorId(idDaPaleta));
  const [icones, definirIcones] = useState<IdDoIcone[]>(restaurado?.icones ?? []);

  const [vista, definirVista] = useState<Vista>(restaurado || !origem.laudo ? "previa" : "avaliacao");
  const [mostrando, definirMostrando] = useState<Mostrando>("gerado");
  const [gerados, definirGerados] = useState<Partial<Record<Audiencia, Montagem>>>(
    restaurado ? { [restaurado.audiencia]: restaurado } : {},
  );
  const [rodada, definirRodada] = useState(0);
  const [gerando, definirGerando] = useState(false);

  const [designGuardado, definirDesignGuardado] = useState(false);
  const [historicoGuardado, definirHistoricoGuardado] = useState(false);
  const [paraExportar, definirParaExportar] = useState<Montagem | null>(null);
  const [erroDaExportacao, definirErroDaExportacao] = useState<string | null>(null);
  const recipiente = useRef<HTMLDivElement>(null);

  // As Âncoras da Célula: ficam no cache, então a busca acontece uma vez por Audiência.
  const idRemoto = origem.ancoras === undefined ? execucaoId : null;
  const chaveDasAncoras = idRemoto === null ? "ancoras:nenhuma" : `ancoras:${idRemoto}:${origem.audiencia}`;
  const buscarAncoras = (): Promise<AncoraDeQuadro[]> =>
    idRemoto === null
      ? Promise.resolve(SEM_ANCORAS)
      : obterAncorasDaCelula(idRemoto, origem.audiencia, "carrossel").then((lista) => lista.map(ancoraDeQuadro));
  const { dados: ancorasDoServidor } = usarDados(chaveDasAncoras, buscarAncoras);
  const ancoras = origem.ancoras ?? ancorasDoServidor ?? SEM_ANCORAS;

  const quadros = useMemo(
    () => montarQuadros({ slides: origem.slides, preferida: composicao, ancoras, icones }),
    [origem.slides, composicao, ancoras, icones],
  );

  const gerado = gerados[audiencia] ?? null;
  const exemplo = referenciaId ? ((referencias ?? []).find((r) => r.identificador === referenciaId) ?? null) : null;

  useEffect(() => {
    if (!designGuardado) return;
    const temporizador = window.setTimeout(() => definirDesignGuardado(false), MOSTRA_O_FEITO_MS);
    return () => window.clearTimeout(temporizador);
  }, [designGuardado]);

  useEffect(() => {
    if (!historicoGuardado) return;
    const temporizador = window.setTimeout(() => definirHistoricoGuardado(false), MOSTRA_O_FEITO_MS);
    return () => window.clearTimeout(temporizador);
  }, [historicoGuardado]);

  // A exportação roda quando os quadros em tamanho real já estão montados fora da tela.
  useEffect(() => {
    if (!paraExportar) return;
    let cancelado = false;
    void (async () => {
      try {
        await garantirFontes();
        await esperarMontagem();
        const nos = Array.from(recipiente.current?.querySelectorAll<HTMLElement>("[data-quadro]") ?? []);
        const imagens = await fotografarQuadros(nos);
        if (!cancelado) baixarArquivo(zipDosQuadros(imagens), nomeDoZip(paraExportar.audiencia));
      } catch {
        if (!cancelado) definirErroDaExportacao("Não consegui montar o zip. Tente de novo.");
      } finally {
        if (!cancelado) definirParaExportar(null);
      }
    })();
    return () => {
      cancelado = true;
    };
  }, [paraExportar]);

  const quadrosDoGerado = useMemo(() => (gerado ? quadrosDaMontagem(gerado) : []), [gerado]);
  const quadrosDoExemplo = useMemo(() => (exemplo ? montarQuadrosDeExemplo(exemplo) : []), [exemplo]);
  const quadrosParaExportar = useMemo(() => (paraExportar ? quadrosDaMontagem(paraExportar) : []), [paraExportar]);

  function escolherComposicao(escolhida: Composicao) {
    definirComposicao(escolhida);
    if (exemplo && exemplo.composicao !== escolhida) {
      definirReferenciaId(null);
      definirMostrando("gerado");
    }
  }

  function escolherExemplo(identificador: string, composicaoDele: string) {
    if (referenciaId === identificador) {
      definirReferenciaId(null);
      definirMostrando("gerado");
      return;
    }
    definirReferenciaId(identificador);
    // Referência de família visual: o editor não a desenha, então mantém a composição atual e
    // mostra a miniatura dela; o servidor usa a família quando o pedido leva essa referência.
    if (ehComposicao(composicaoDele)) definirComposicao(composicaoDele);
    definirMostrando("exemplo");
    definirVista("previa");
  }

  function escolherPaleta(escolhida: Paleta) {
    definirPaleta(escolhida);
    aoEscolherPaleta(escolhida.id);
  }

  function alternarIcone(id: IdDoIcone) {
    definirIcones((atuais) => (atuais.includes(id) ? atuais.filter((outro) => outro !== id) : [...atuais, id]));
  }

  async function gerar() {
    definirGerando(true);
    try {
      const lista =
        idRemoto !== null && ancorasDoServidor === undefined
          ? ((await buscar(chaveDasAncoras, buscarAncoras)) ?? [])
          : ancoras;
      definirGerados((atuais) => ({
        ...atuais,
        [audiencia]: { audiencia, slides: origem.slides, composicao, referenciaId, paleta, icones, ancoras: lista },
      }));
      definirRodada((atual) => atual + 1);
      definirMostrando("gerado");
      definirVista("previa");
    } finally {
      definirGerando(false);
    }
  }

  function salvarNoHistorico() {
    if (!gerado) return;
    salvar({
      especie: "carrossel",
      titulo,
      resumo: `${pluralizar(gerado.slides.length, "quadro", "quadros")} · ${rotuloDaComposicao(gerado.composicao)}`,
      audiencia: gerado.audiencia,
      execucaoId,
      dados: dadosParaSalvar(gerado, origem.laudo),
    });
    definirHistoricoGuardado(true);
  }

  function exportar() {
    if (!gerado) return;
    definirErroDaExportacao(null);
    definirParaExportar(gerado);
  }

  // Com um exemplo na tela, os botões de baixo não valem: eles agem no carrossel gerado, que não está à vista.
  const exemploNaTela = vista === "previa" && mostrando === "exemplo" && exemplo !== null;
  const designAtual: Design = { composicao, referencia: referenciaId };
  const designJaGuardado = mesmoDesign(design, designAtual);

  const esquerda = (
    <>
      <div className="flex items-center justify-between gap-4">
        <Titulo>Carrossel</Titulo>
        <button
          type="button"
          onClick={acaoDoTitulo.aoClicar}
          aria-label={acaoDoTitulo.rotulo}
          title={acaoDoTitulo.rotulo}
          className="grid h-10 w-10 place-items-center rounded-full text-claro transition-colors duration-150 hover:bg-superficie"
        >
          {acaoDoTitulo.icone}
        </button>
      </div>

      <div className="mt-6">
        <Pilulas<Audiencia>
          rotuloAcessivel="Audiência"
          valor={audiencia}
          onMudar={definirAudiencia}
          opcoes={AUDIENCIAS.filter((a) => origens.some((o) => o.audiencia === a)).map((a) => ({
            valor: a,
            rotulo: rotuloAudiencia(a),
          }))}
        />
      </div>

      <section className="mt-10" aria-labelledby="carrossel-quadros">
        <div id="carrossel-quadros">
          <TituloDeSecao>Quadros</TituloDeSecao>
        </div>
        <div className="mt-6">
          <Quadros key={origem.audiencia} quadros={quadros} ancoras={ancoras} />
        </div>
      </section>

      <section className="mt-14" aria-labelledby="carrossel-visual">
        <div id="carrossel-visual">
          <TituloDeSecao>Configurações visuais</TituloDeSecao>
        </div>

        <div className="mt-8">
          <Rotulo>Tipos</Rotulo>
          <div className="mt-4">
            <EscolhaDeComposicao valor={composicao} aoEscolher={escolherComposicao} />
          </div>
        </div>

        <div className="mt-10">
          <Rotulo>Exemplos</Rotulo>
          <div className="mt-4">
            <EscolhaDeExemplo
              referencias={referencias}
              erro={erroDasReferencias?.message ?? null}
              escolhida={referenciaId}
              aoEscolher={(r) => escolherExemplo(r.identificador, r.composicao)}
            />
          </div>
          <div className="mt-4 flex justify-end">
            <Botao
              variante="escuro"
              disabled={designJaGuardado && !designGuardado}
              icone={designGuardado ? <IconeMarca size={18} strokeWidth={2.5} /> : undefined}
              onClick={() => {
                aoSalvarDesign(designAtual);
                definirDesignGuardado(true);
              }}
            >
              {designGuardado || designJaGuardado ? "Design salvo" : "Salvar design"}
            </Botao>
          </div>
        </div>

        <div className="mt-10">
          <Rotulo>Paletas</Rotulo>
          <div className="mt-4">
            <EscolhaDePaleta valor={paleta.id} aoEscolher={escolherPaleta} />
          </div>
        </div>

        <div className="mt-10">
          <Rotulo>Ícones que não podem faltar</Rotulo>
          <div className="mt-4">
            <EscolhaDeIcones marcados={icones} aoAlternar={alternarIcone} />
          </div>
        </div>

        <div className="mt-12">
          <Botao
            variante="claro"
            tamanho="grande"
            disabled={gerando || quadros.length === 0}
            onClick={() => void gerar()}
          >
            {gerando ? "Gerando…" : "Gerar carrossel"}
          </Botao>
        </div>
      </section>
    </>
  );

  let corpo: ReactNode;
  if (vista === "avaliacao") {
    const barras = barrasDoLaudo(origem.laudo);
    corpo =
      barras.length > 0 ? (
        <div key={`avaliacao-${audiencia}`} className="surge mx-auto w-full max-w-[560px]">
          <Barras barras={barras} />
        </div>
      ) : (
        <Vazio titulo="Esta Célula não tem Laudo." />
      );
  } else if (mostrando === "exemplo" && exemplo) {
    const imagem = exemplo.imagem_disponivel ? urlDaImagemDaReferencia(exemplo.identificador) : null;
    // Família visual: só existe a imagem do exemplo, nenhum quadro do editor a representa.
    const desenhavel = ehComposicao(exemplo.composicao);
    const nos = quadrosDoExemplo
      .slice(0, imagem && !desenhavel ? 1 : undefined)
      .map((quadro, indice) =>
      indice === 0 && imagem ? (
        <img
          key="imagem"
          src={imagem}
          alt={`Exemplo: ${exemplo.titulo}`}
          className="h-full w-full object-cover"
          style={{ width: 1080, height: 1350 }}
        />
      ) : (
        <Quadro key={quadro.indice} quadro={quadro} paleta={paleta} selo="Exemplo" />
      ),
    );
    corpo = (
      <div key={`exemplo-${exemplo.identificador}`} className="surge flex flex-col items-center gap-4">
        <Celular quadros={nos} legenda={exemplo.titulo} rotuloAcessivel={`Exemplo: ${exemplo.titulo}`} />
        <p className="text-[12px] font-medium uppercase tracking-[0.02em] text-etiqueta">Conteúdo de amostra</p>
      </div>
    );
  } else if (gerado) {
    const nos = quadrosDoGerado.map((quadro) => (
      <Quadro key={quadro.indice} quadro={quadro} paleta={gerado.paleta} selo={rotuloAudiencia(gerado.audiencia)} />
    ));
    corpo = (
      <div key={`gerado-${audiencia}-${rodada}`} className="surge">
        <Celular quadros={nos} legenda={gerado.slides[0]?.titulo ?? ""} rotuloAcessivel="Carrossel gerado" />
      </div>
    );
  } else {
    corpo = (
      <Vazio
        titulo="Gere o carrossel ou escolha um exemplo."
        acao={
          <Botao variante="claro" tamanho="pequeno" disabled={gerando} onClick={() => void gerar()}>
            Gerar carrossel
          </Botao>
        }
      />
    );
  }

  const direita = (
    <>
      <TopoDaPrevia esquerda={<IlhaDaVista vista={vista} aoMudar={definirVista} />} />
      <CorpoDaPrevia>
        <div className="flex min-h-full flex-col items-center justify-center">{corpo}</div>
      </CorpoDaPrevia>
      <footer className="flex shrink-0 flex-wrap items-center justify-end gap-3 px-5 pb-8 pt-3 lg:px-[50px]">
        {erroDaExportacao && (
          <p role="alert" className="mr-auto text-[14px] text-coral-claro">
            {erroDaExportacao}
          </p>
        )}
        <Botao
          variante="escuro"
          disabled={!gerado || exemploNaTela}
          icone={historicoGuardado ? <IconeMarca size={18} strokeWidth={2.5} /> : <IconeSalvar size={18} />}
          onClick={salvarNoHistorico}
        >
          {historicoGuardado ? "Salvo" : "Salvar no histórico"}
        </Botao>
        <Botao
          variante="claro"
          disabled={!gerado || exemploNaTela || paraExportar !== null}
          icone={paraExportar ? <IconeGirando size={18} className="animate-spin" /> : <IconeBaixar size={18} />}
          onClick={exportar}
        >
          {paraExportar ? "Exportando…" : "Exportar carrossel"}
        </Botao>
      </footer>
    </>
  );

  return (
    <>
      <Divisao esquerda={esquerda} direita={direita} larguraDaColuna={560} />
      {paraExportar &&
        createPortal(
          <div
            ref={recipiente}
            aria-hidden="true"
            style={{ position: "fixed", left: -20000, top: 0, pointerEvents: "none" }}
          >
            {quadrosParaExportar.map((quadro: QuadroMontado) => (
              <Quadro
                key={quadro.indice}
                quadro={quadro}
                paleta={paraExportar.paleta}
                selo={rotuloAudiencia(paraExportar.audiencia)}
              />
            ))}
          </div>,
          document.body,
        )}
    </>
  );
}
