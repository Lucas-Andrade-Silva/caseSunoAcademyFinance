// O editor do carrossel, com o conteúdo já pronto. À esquerda: os quadros (texto e direção da imagem)
// e as configurações visuais em ordem (familia, tipo, paleta, ícones) com o botão Gerar carrossel. À
// direita: as barras do Laudo ou o celular de feed. No Suno escuro o celular mostra o carrossel ao
// vivo, com cada mudança; nas outras famílias, o exemplo do Layout até o servidor montar o carrossel.
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import {
  AUDIENCIAS,
  editarTextoDaCelula,
  listarFamiliasVisuais,
  listarReferenciasVisuais,
  obterAncorasDaCelula,
  urlDaPreviaDaReferencia,
  urlDaPreviaDoSlide,
  type Audiencia,
  type Laudo,
  type Slide,
} from "../../dados/cliente";
import Barras from "../../interface/Barras";
import Botao from "../../interface/Botao";
import { CorpoDaPrevia, Divisao, Rotulo, TituloDaGuia, TituloDeSecao, TopoDaPrevia } from "../../interface/Divisao";
import { IconeBaixar, IconeGirando, IconeMarca, IconeSalvar } from "../../interface/Icones";
import { Pilulas } from "../../interface/Pilulas";
import Vazio from "../../interface/Vazio";
import { urlDoZipDoPacote } from "../../dados/cliente";
import { buscar, usarDados } from "../../nucleo/dados";
import { usarHistorico } from "../../nucleo/historico";
import { barrasDoLaudo } from "../../nucleo/laudo";
import { CHAVES } from "../../nucleo/precarga";
import { pluralizar, rotuloAudiencia } from "../../texto/rotulos";
import Celular from "./Celular";
import { COMPOSICAO_PADRAO, rotuloDaComposicao } from "./composicoes";
import { dadosParaSalvar } from "./dadosSalvos";
import { mesmoDesign } from "./design";
import EscolhaDeComposicao from "./EscolhaDeComposicao";
import EscolhaDeFamilia from "./EscolhaDeFamilia";
import EscolhaDeIcones from "./EscolhaDeIcones";
import EscolhaDeLayout from "./EscolhaDeLayout";
import EscolhaDePaleta from "./EscolhaDePaleta";
import {
  SUNO_ESCURO,
  familiaDaReferencia,
  opcoesDeFamilia,
  referenciaDaComposicao,
  type OpcaoDeFamilia,
} from "./familias";
import { baixarArquivo, fotografarQuadros, zipDosQuadros } from "./exportar";
import { ancoraDeQuadro } from "./graficos";
import type {
  AncoraDeQuadro,
  Composicao,
  Design,
  IdDoIcone,
  Montagem,
  Paleta,
  QuadroMontado,
} from "./modelo";
import { montarQuadros, quadrosDaMontagem } from "./montagem";
import { nomeDoZip } from "./nomesDeArquivo";
import { montarNoServidor } from "./renderDoServidor";
import { paletaParaServidor, paletaPorId } from "./paletas";
import Quadro from "./Quadro";
import Quadros, { type CamposEditaveis } from "./Quadros";
import { garantirFontes } from "./tipografia";

type Vista = "avaliacao" | "previa";

/** O carrossel que o servidor renderizou com o design de uma família visual. */
interface RenderDoServidor {
  referenciaId: string;
  titulo: string;
  urls: readonly string[];
  /** A paleta com que o servidor montou: os PNGs (e o zip) só têm essa. */
  paletaId: string;
}

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
  /** O ícone redondo ao lado do título: sair do salvo. Na sessão a nova geração mora na barra lateral. */
  acaoDoTitulo?: { rotulo: string; icone: ReactNode; aoClicar: () => void };
}

const SEM_ANCORAS: AncoraDeQuadro[] = [];
const MOSTRA_O_FEITO_MS = 1800;

/** Um respiro para o React terminar de montar os quadros; temporizador, não quadro de animação, porque aba escondida não anima. */
function esperarMontagem(): Promise<void> {
  return new Promise((resolver) => window.setTimeout(resolver, 80));
}

function IlhaDaVista({ vista, aoMudar }: { vista: Vista; aoMudar: (vista: Vista) => void }) {
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
  const { dados: referencias, erro: erroDasReferencias } = usarDados(
    CHAVES.referencias,
    listarReferenciasVisuais,
  );
  const { dados: papeisDasFamilias } = usarDados(CHAVES.familias, listarFamiliasVisuais);

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
  const [gerados, definirGerados] = useState<Partial<Record<Audiencia, Montagem>>>(
    restaurado ? { [restaurado.audiencia]: restaurado } : {},
  );
  const [rodada, definirRodada] = useState(0);
  const [gerando, definirGerando] = useState(false);
  const [noServidor, definirNoServidor] = useState<Partial<Record<Audiencia, RenderDoServidor>>>({});
  const [erroDoServidor, definirErroDoServidor] = useState<string | null>(null);

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
      : obterAncorasDaCelula(idRemoto, origem.audiencia, "carrossel").then((lista) =>
          lista.map(ancoraDeQuadro),
        );
  const { dados: ancorasDoServidor } = usarDados(chaveDasAncoras, buscarAncoras);
  const ancoras = origem.ancoras ?? ancorasDoServidor ?? SEM_ANCORAS;

  // O texto que a pessoa corrigiu nos quadros vale no lugar do gerado: prévia, salvo e exportação o usam.
  const [editados, definirEditados] = useState<Partial<Record<Audiencia, Slide[]>>>({});
  const slides = editados[origem.audiencia] ?? origem.slides;
  const textoEditado = editados[origem.audiencia] !== undefined;
  // O Laudo que o servidor devolveu depois de julgar o texto editado, por Audiência.
  const [laudosNovos, definirLaudosNovos] = useState<Partial<Record<Audiencia, Laudo>>>({});
  const [textoSalvo, definirTextoSalvo] = useState<Partial<Record<Audiencia, boolean>>>({});
  const [salvandoTexto, definirSalvandoTexto] = useState(false);
  const [erroDoTexto, definirErroDoTexto] = useState<string | null>(null);
  const laudo = laudosNovos[origem.audiencia] ?? origem.laudo;

  async function salvarTexto() {
    if (execucaoId === null) return;
    definirSalvandoTexto(true);
    definirErroDoTexto(null);
    try {
      const novo = await editarTextoDaCelula(execucaoId, origem.audiencia, "carrossel", {
        slides: slides.map(({ titulo, corpo }) => ({ titulo, corpo })),
      });
      definirLaudosNovos((atuais) => ({ ...atuais, [origem.audiencia]: novo }));
      definirTextoSalvo((atuais) => ({ ...atuais, [origem.audiencia]: true }));
      definirVista("avaliacao");
    } catch (erro) {
      definirErroDoTexto(erro instanceof Error ? erro.message : "Não consegui salvar o texto.");
    } finally {
      definirSalvandoTexto(false);
    }
  }

  function editarQuadro(indice: number, campos: Partial<CamposEditaveis>) {
    definirTextoSalvo((atuais) => ({ ...atuais, [origem.audiencia]: false }));
    definirEditados((atuais) => {
      const base = atuais[origem.audiencia] ?? origem.slides;
      const lista = base.map((slide, i) => {
        if (i !== indice) return slide;
        const novo = { ...slide, ...campos };
        // O destaque precisa aparecer literalmente no título: se o título mudou e ele sumiu, sai.
        if (novo.destaque && !novo.titulo.includes(novo.destaque)) novo.destaque = null;
        return novo;
      });
      return { ...atuais, [origem.audiencia]: lista };
    });
  }

  const quadros = useMemo(
    () => montarQuadros({ slides, preferida: composicao, ancoras, icones }),
    [slides, composicao, ancoras, icones],
  );

  const exemplo = referenciaId
    ? ((referencias ?? []).find((r) => r.identificador === referenciaId) ?? null)
    : null;
  const familia = familiaDaReferencia(exemplo);
  const sunoEscuro = familia === SUNO_ESCURO;
  const opcoesDaFamilia = useMemo(
    () => opcoesDeFamilia(referencias ?? [], papeisDasFamilias, slides),
    [referencias, papeisDasFamilias, slides],
  );
  const opcaoDaFamilia = opcoesDaFamilia.find((opcao) => opcao.valor === familia) ?? null;
  // No Suno escuro, o carrossel gerado acompanha as escolhas: mudar tipo, paleta ou ícones muda a prévia,
  // o salvo e o exportado. Numa família ele não existe no navegador; quem desenha é o servidor.
  const guardado = gerados[audiencia];
  const gerado: Montagem | null =
    sunoEscuro && guardado
      ? {
          audiencia,
          slides,
          composicao,
          referenciaId,
          paleta,
          icones,
          ancoras: ancoras.length > 0 ? ancoras : guardado.ancoras,
        }
      : null;

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

  const quadrosParaExportar = useMemo(
    () => (paraExportar ? quadrosDaMontagem(paraExportar) : []),
    [paraExportar],
  );

  function escolherFamilia(opcao: OpcaoDeFamilia) {
    definirReferenciaId(
      opcao.valor === SUNO_ESCURO
        ? referenciaDaComposicao(referencias ?? [], composicao)
        : (opcao.layouts[0]?.identificador ?? null),
    );
    definirErroDoServidor(null);
    definirVista("previa");
  }

  function escolherComposicao(escolhida: Composicao) {
    definirComposicao(escolhida);
    definirReferenciaId(referenciaDaComposicao(referencias ?? [], escolhida));
    definirVista("previa");
  }

  function escolherLayout(identificador: string) {
    definirReferenciaId(identificador);
    definirErroDoServidor(null);
    definirVista("previa");
  }

  function escolherPaleta(escolhida: Paleta) {
    definirPaleta(escolhida);
    aoEscolherPaleta(escolhida.id);
    definirVista("previa");
  }

  function alternarIcone(id: IdDoIcone) {
    definirIcones((atuais) =>
      atuais.includes(id) ? atuais.filter((outro) => outro !== id) : [...atuais, id],
    );
    definirVista("previa");
  }

  // Numa família, o navegador não desenha: o servidor monta o carrossel com o layout escolhido.
  const exemploDeFamilia = !sunoEscuro && exemplo !== null;

  async function gerarNoServidor(referencia: NonNullable<typeof exemplo>) {
    if (execucaoId === null) {
      definirErroDoServidor("Este exemplo só vale numa geração nova: abra uma Saída gerada para montá-lo.");
      return;
    }
    definirGerando(true);
    definirErroDoServidor(null);
    try {
      const urls = await montarNoServidor(
        execucaoId,
        audiencia,
        referencia.identificador,
        paletaParaServidor(paleta),
      );
      definirNoServidor((atuais) => ({
        ...atuais,
        [audiencia]: {
          referenciaId: referencia.identificador,
          titulo: referencia.titulo,
          urls,
          paletaId: paleta.id,
        },
      }));
      definirRodada((atual) => atual + 1);
      definirVista("previa");
    } catch (erro) {
      definirErroDoServidor(
        erro instanceof Error ? erro.message : "Não consegui montar o carrossel no servidor.",
      );
    } finally {
      definirGerando(false);
    }
  }

  async function gerar() {
    if (exemplo !== null && exemploDeFamilia) {
      await gerarNoServidor(exemplo);
      return;
    }
    definirErroDoServidor(null);
    definirGerando(true);
    try {
      const lista =
        idRemoto !== null && ancorasDoServidor === undefined
          ? ((await buscar(chaveDasAncoras, buscarAncoras)) ?? [])
          : ancoras;
      definirGerados((atuais) => ({
        ...atuais,
        [audiencia]: {
          audiencia,
          slides,
          composicao,
          referenciaId,
          paleta,
          icones,
          ancoras: lista,
        },
      }));
      definirRodada((atual) => atual + 1);
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
      dados: dadosParaSalvar(gerado, laudo),
    });
    definirHistoricoGuardado(true);
  }

  function exportar() {
    if (!gerado) return;
    definirErroDaExportacao(null);
    definirParaExportar(gerado);
  }

  // O render do servidor só vale enquanto o layout escolhido é o mesmo com que ele foi montado.
  const montadoAgora = noServidor[audiencia];
  const doServidor = montadoAgora && montadoAgora.referenciaId === referenciaId ? montadoAgora : null;
  // A prévia recolore na hora, mas o zip é dos PNGs: com outra paleta, só depois de gerar de novo.
  const paletaDoRender = doServidor !== null && doServidor.paletaId === paleta.id;
  const servidorNaTela = !sunoEscuro && vista === "previa" && doServidor !== null && paletaDoRender;
  const indisponivel = opcaoDaFamilia?.indisponivel ?? null;
  const designAtual: Design = { composicao, referencia: referenciaId };
  const designJaGuardado = mesmoDesign(design, designAtual);

  const esquerda = (
    <>
      <div className="flex items-center justify-between gap-4">
        <TituloDaGuia>Carrossel</TituloDaGuia>
        {acaoDoTitulo && (
          <button
            type="button"
            onClick={acaoDoTitulo.aoClicar}
            aria-label={acaoDoTitulo.rotulo}
            title={acaoDoTitulo.rotulo}
            className="grid h-10 w-10 place-items-center rounded-full text-claro transition-colors duration-150 hover:bg-superficie"
          >
            {acaoDoTitulo.icone}
          </button>
        )}
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
          <Quadros key={origem.audiencia} quadros={quadros} ancoras={ancoras} aoEditar={editarQuadro} />
          {textoEditado && (
            <div className="mt-4">
              <p className="text-[13px] text-etiqueta">
                {textoSalvo[origem.audiencia]
                  ? "Texto salvo e reavaliado: veja o Laudo em Avaliação. Toque em Gerar carrossel para a prévia."
                  : "Texto editado. Toque em Gerar carrossel para ver a prévia; salve para reavaliar no Laudo e valer nos exemplos do servidor."}
              </p>
              {execucaoId !== null && !textoSalvo[origem.audiencia] && (
                <div className="mt-3">
                  <Botao
                    variante="claro"
                    tamanho="pequeno"
                    disabled={salvandoTexto}
                    onClick={() => void salvarTexto()}
                  >
                    {salvandoTexto ? "Reavaliando…" : "Salvar texto e reavaliar"}
                  </Botao>
                </div>
              )}
              {erroDoTexto && (
                <p role="alert" className="mt-3 text-[14px] text-coral-claro">
                  {erroDoTexto}
                </p>
              )}
            </div>
          )}
        </div>
      </section>

      <section className="mt-14" aria-labelledby="carrossel-visual">
        <div id="carrossel-visual">
          <TituloDeSecao>Configurações visuais</TituloDeSecao>
        </div>

        <div className="mt-8">
          <Rotulo>Família</Rotulo>
          <div className="mt-4">
            {referencias ? (
              <EscolhaDeFamilia opcoes={opcoesDaFamilia} valor={familia} aoEscolher={escolherFamilia} />
            ) : erroDasReferencias ? (
              <p role="alert" className="py-2 text-[14px] leading-snug text-coral-claro">
                Não consegui buscar as famílias visuais. {erroDasReferencias.message}
              </p>
            ) : (
              <span className="pulsa block h-[112px] rounded-lg bg-superficie" aria-hidden="true" />
            )}
          </div>
        </div>

        <div className="mt-10">
          <Rotulo>Tipos</Rotulo>
          <div className="mt-4">
            {sunoEscuro ? (
              <EscolhaDeComposicao valor={composicao} aoEscolher={escolherComposicao} />
            ) : (
              <EscolhaDeLayout
                layouts={opcaoDaFamilia?.layouts ?? []}
                valor={referenciaId}
                aoEscolher={(referencia) => escolherLayout(referencia.identificador)}
              />
            )}
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

        {sunoEscuro ? (
          <div className="mt-10">
            <Rotulo>Ícones que não podem faltar</Rotulo>
            <div className="mt-4">
              <EscolhaDeIcones marcados={icones} aoAlternar={alternarIcone} />
            </div>
          </div>
        ) : (
          <p className="mt-10 text-[13px] text-etiqueta">Ícones: só no Suno escuro.</p>
        )}

        <div className="mt-12">
          <Botao
            variante="claro"
            tamanho="grande"
            disabled={gerando || quadros.length === 0 || indisponivel !== null}
            onClick={() => void gerar()}
          >
            {gerando ? (exemploDeFamilia ? "Montando no servidor…" : "Gerando…") : "Gerar carrossel"}
          </Botao>
          {indisponivel && (
            <p role="alert" className="mt-3 text-[14px] text-coral-claro">
              A Família {opcaoDaFamilia?.rotulo} não monta este carrossel ({indisponivel.toLowerCase()}).
              Escolha outra família.
            </p>
          )}
          {exemploDeFamilia && !erroDoServidor && !indisponivel && (
            <p className="mt-3 text-[13px] text-etiqueta">
              Este exemplo é desenhado pelo servidor, com as fotos do assunto. Pode levar cerca de um minuto.
            </p>
          )}
          {erroDoServidor && (
            <p role="alert" className="mt-3 text-[14px] text-coral-claro">
              {erroDoServidor}
            </p>
          )}
        </div>
      </section>
    </>
  );

  let corpo: ReactNode;
  if (vista === "avaliacao") {
    const barras = barrasDoLaudo(laudo);
    corpo =
      barras.length > 0 ? (
        <div key={`avaliacao-${audiencia}`} className="surge mx-auto w-full max-w-[560px]">
          <Barras barras={barras} />
        </div>
      ) : (
        <Vazio titulo="Esta Célula não tem Laudo." />
      );
  } else if (sunoEscuro) {
    // Ao vivo: os quadros com as escolhas de agora, antes mesmo de gerar.
    const nos = quadros.map((quadro) => (
      <Quadro key={quadro.indice} quadro={quadro} paleta={paleta} selo={rotuloAudiencia(audiencia)} />
    ));
    corpo =
      nos.length > 0 ? (
        <div key={`sunoEscuro-${audiencia}-${rodada}`} className="surge flex flex-col items-center gap-4">
          <Celular quadros={nos} legenda={slides[0]?.titulo ?? ""} rotuloAcessivel="Prévia do carrossel" />
          <p className="text-[12px] font-medium uppercase tracking-[0.02em] text-etiqueta">
            {rotuloDaComposicao(composicao)} · {paleta.nome} · {gerado ? "gerado" : "prévia ao vivo"}
          </p>
        </div>
      ) : (
        <Vazio titulo="Esta Célula não tem quadros." />
      );
  } else if (doServidor && execucaoId !== null) {
    // Os slides montados, em HTML, recoloridos pelo servidor com a paleta de agora.
    const nos = doServidor.urls.map((url, indice) => (
      <iframe
        key={`${url}-${paleta.id}`}
        src={urlDaPreviaDoSlide(execucaoId, audiencia, indice + 1, paletaParaServidor(paleta))}
        title={`Quadro ${indice + 1} do carrossel: ${doServidor.titulo}`}
        className="pointer-events-none border-0"
        style={{ width: 1080, height: 1350 }}
      />
    ));
    corpo = (
      <div key={`servidor-${audiencia}-${rodada}`} className="surge flex flex-col items-center gap-4">
        <Celular
          quadros={nos}
          legenda={origem.slides[0]?.titulo ?? ""}
          rotuloAcessivel={`Carrossel montado com ${doServidor.titulo}`}
        />
        <p className="max-w-[320px] text-center text-[12px] font-medium uppercase tracking-[0.02em] text-etiqueta">
          {doServidor.titulo} · {paleta.nome}
          {paletaDoRender ? "" : " · gere de novo para exportar"}
        </p>
      </div>
    );
  } else if (exemplo) {
    corpo = (
      <div key={`exemplo-${exemplo.identificador}`} className="surge flex flex-col items-center gap-4">
        <Celular
          quadros={[
            <iframe
              key={`${exemplo.identificador}-${paleta.id}`}
              src={urlDaPreviaDaReferencia(exemplo.identificador, paletaParaServidor(paleta))}
              title={`Exemplo: ${exemplo.titulo}`}
              className="pointer-events-none border-0"
              style={{ width: 1080, height: 1350 }}
            />,
          ]}
          legenda={exemplo.titulo}
          rotuloAcessivel={`Exemplo: ${exemplo.titulo}`}
        />
        <p className="max-w-[320px] text-center text-[12px] font-medium uppercase tracking-[0.02em] text-etiqueta">
          Exemplo do Layout · {paleta.nome}
        </p>
      </div>
    );
  } else {
    corpo = <Vazio titulo="Escolha um Layout da família." />;
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
          disabled={!gerado}
          icone={historicoGuardado ? <IconeMarca size={18} strokeWidth={2.5} /> : <IconeSalvar size={18} />}
          onClick={salvarNoHistorico}
        >
          {historicoGuardado ? "Salvo" : "Salvar no histórico"}
        </Botao>
        <Botao
          variante="claro"
          disabled={(!gerado && !servidorNaTela) || paraExportar !== null}
          icone={
            paraExportar ? <IconeGirando size={18} className="animate-spin" /> : <IconeBaixar size={18} />
          }
          onClick={
            servidorNaTela && execucaoId !== null
              ? () => window.location.assign(urlDoZipDoPacote(execucaoId, audiencia, "carrossel"))
              : exportar
          }
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
            style={{
              position: "fixed",
              left: -20000,
              top: 0,
              pointerEvents: "none",
            }}
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
