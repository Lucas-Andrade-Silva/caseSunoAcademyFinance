// O Histórico: o que a pessoa salvou nas guias de conteúdo (neste navegador) e as Saídas que o
// servidor gerou. Escolher uma linha mostra a prévia à direita; "Abrir" leva o conteúdo de volta
// para a guia dele.
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { listarExecucoes, type ExecucaoResumo, type Formato } from "../../dados/cliente";
import Botao from "../../interface/Botao";
import { CorpoDaPrevia, Divisao, Ilha, Titulo, TituloDeSecao, TopoDaPrevia } from "../../interface/Divisao";
import { IconeCarrossel, IconeIngestao, IconeLixo, IconeTexto, IconeVideo } from "../../interface/Icones";
import Linha, { type CorDoQuadrado } from "../../interface/Linha";
import { Pilulas } from "../../interface/Pilulas";
import Vazio from "../../interface/Vazio";
import { usarDados } from "../../nucleo/dados";
import { guiaDoCaminho, guiaDoFormato } from "../../nucleo/guias";
import { usarHistorico, type EspecieSalva, type Salvo } from "../../nucleo/historico";
import { CHAVES } from "../../nucleo/precarga";
import { usarSessoes } from "../../nucleo/sessao";
import { formatarDataCurta, rotuloAudiencia, rotuloFormato } from "../../texto/rotulos";
import PreviaDoCarrossel from "../carrossel/PreviaSalva";
import PreviaDoTexto from "../texto/PreviaSalva";
import PreviaDoVideo from "../video/PreviaSalva";

type Filtro = "todos" | EspecieSalva;

const DA_ESPECIE: Record<EspecieSalva, { cor: CorDoQuadrado; icone: ReactNode; rotulo: string }> = {
  texto: { cor: "azul", icone: <IconeTexto size={20} />, rotulo: "Texto" },
  carrossel: { cor: "roxo", icone: <IconeCarrossel size={20} />, rotulo: "Carrossel" },
  video: { cor: "coral", icone: <IconeVideo size={20} />, rotulo: "Vídeo" },
};

const FORMATO_DA_ESPECIE: Record<EspecieSalva, Formato> = {
  texto: "texto_analitico",
  carrossel: "carrossel",
  video: "roteiro",
};

type Escolha = { origem: "salvo"; id: string } | { origem: "geracao"; id: string } | null;

function formatosDa(execucao: ExecucaoResumo): Formato[] {
  const formatos = new Set<Formato>();
  for (const posicao of execucao.posicoes) {
    if (!posicao.sem_conteudo) formatos.add(posicao.formato);
  }
  return (["texto_analitico", "carrossel", "roteiro"] as const).filter((f) => formatos.has(f));
}

function PreviaDoSalvo({ salvo }: { salvo: Salvo }) {
  if (salvo.especie === "texto") return <PreviaDoTexto salvo={salvo} />;
  if (salvo.especie === "carrossel") return <PreviaDoCarrossel salvo={salvo} />;
  return <PreviaDoVideo salvo={salvo} />;
}

export default function GuiaHistorico() {
  const { salvos, remover, pedirAbertura } = usarHistorico();
  const sessoes = usarSessoes();
  const navegar = useNavigate();
  const { pathname } = useLocation();
  const naTela = guiaDoCaminho(pathname)?.id === "historico";
  const { dados: execucoes, recarregar } = usarDados(CHAVES.execucoes, listarExecucoes, {
    atualizarACada: (lista) => (lista.some((e) => e.status === "na_fila" || e.status === "gerando") ? 3000 : null),
  });
  const [filtro, definirFiltro] = useState<Filtro>("todos");
  const [escolha, definirEscolha] = useState<Escolha>(null);
  const [confirmandoRemocao, definirConfirmandoRemocao] = useState(false);

  useEffect(() => {
    if (naTela) void recarregar();
  }, [naTela, recarregar]);

  useEffect(() => {
    if (!confirmandoRemocao) return;
    const temporizador = window.setTimeout(() => definirConfirmandoRemocao(false), 3000);
    return () => window.clearTimeout(temporizador);
  }, [confirmandoRemocao]);

  const salvosFiltrados = useMemo(
    () => salvos.filter((s) => filtro === "todos" || s.especie === filtro),
    [salvos, filtro],
  );
  const geracoes = useMemo(
    () =>
      [...(execucoes ?? [])]
        .filter((e) => e.posicoes.length > 0)
        .filter((e) => filtro === "todos" || formatosDa(e).includes(FORMATO_DA_ESPECIE[filtro]))
        .sort((a, b) => b.iniciada_em.localeCompare(a.iniciada_em))
        .slice(0, 30),
    [execucoes, filtro],
  );

  const salvoEscolhido = escolha?.origem === "salvo" ? salvos.find((s) => s.id === escolha.id) : undefined;
  const geracaoEscolhida =
    escolha?.origem === "geracao" ? (execucoes ?? []).find((e) => e.identificador === escolha.id) : undefined;

  function abrirGeracao(execucao: ExecucaoResumo, formato: Formato) {
    void sessoes[formato].abrir(execucao.identificador);
    navegar(guiaDoFormato(formato).caminho);
  }

  const esquerda = (
    <>
      <Titulo>Histórico</Titulo>
      <div className="mt-6">
        <Pilulas<Filtro>
          rotuloAcessivel="Filtrar por formato"
          valor={filtro}
          onMudar={(valor) => {
            definirFiltro(valor);
            definirEscolha(null);
          }}
          opcoes={[
            { valor: "todos", rotulo: "Todos" },
            { valor: "texto", rotulo: "Texto" },
            { valor: "carrossel", rotulo: "Carrossel" },
            { valor: "video", rotulo: "Vídeo" },
          ]}
        />
      </div>

      <div className="mt-8 flex flex-col gap-2.5">
        {salvosFiltrados.length === 0 && <p className="py-2 text-[15px] text-etiqueta">Nada salvo ainda.</p>}
        {salvosFiltrados.map((salvo) => {
          const aparencia = DA_ESPECIE[salvo.especie];
          return (
            <Linha
              key={salvo.id}
              cor={aparencia.cor}
              icone={aparencia.icone}
              titulo={salvo.titulo}
              subtitulo={`${rotuloAudiencia(salvo.audiencia)} · ${salvo.resumo} · ${formatarDataCurta(salvo.criadoEm)}`}
              selecionada={escolha?.origem === "salvo" && escolha.id === salvo.id}
              onClick={() => definirEscolha({ origem: "salvo", id: salvo.id })}
            />
          );
        })}
      </div>

      {geracoes.length > 0 && (
        <>
          <div className="mt-14">
            <TituloDeSecao>Saídas</TituloDeSecao>
          </div>
          <div className="mt-6 flex flex-col gap-2.5">
            {geracoes.map((execucao) => (
              <Linha
                key={execucao.identificador}
                cor="cinza"
                icone={<IconeIngestao size={20} />}
                titulo={execucao.nome}
                subtitulo={`${formatarDataCurta(execucao.iniciada_em)} · ${formatosDa(execucao)
                  .map((f) => rotuloFormato(f))
                  .join(", ")}`}
                selecionada={escolha?.origem === "geracao" && escolha.id === execucao.identificador}
                onClick={() => definirEscolha({ origem: "geracao", id: execucao.identificador })}
              />
            ))}
          </div>
        </>
      )}
    </>
  );

  let topo: ReactNode = <TopoDaPrevia />;
  let corpo: ReactNode = <Vazio titulo="Escolha um conteúdo." />;

  if (salvoEscolhido) {
    topo = (
      <TopoDaPrevia
        esquerda={<Ilha>{DA_ESPECIE[salvoEscolhido.especie].rotulo}</Ilha>}
        direita={
          <>
            <Botao
              variante="escuro"
              icone={<IconeLixo size={18} />}
              aria-label="Apagar do histórico"
              onClick={() => {
                if (!confirmandoRemocao) {
                  definirConfirmandoRemocao(true);
                  return;
                }
                remover(salvoEscolhido.id);
                definirEscolha(null);
                definirConfirmandoRemocao(false);
              }}
            >
              {confirmandoRemocao ? "Confirmar" : ""}
            </Botao>
            <Botao variante="claro" onClick={() => pedirAbertura(salvoEscolhido)}>
              Abrir
            </Botao>
          </>
        }
      />
    );
    corpo = (
      <div key={salvoEscolhido.id} className="surge">
        <PreviaDoSalvo salvo={salvoEscolhido} />
      </div>
    );
  } else if (geracaoEscolhida) {
    const formatos = formatosDa(geracaoEscolhida);
    topo = <TopoDaPrevia esquerda={<Ilha>Saída</Ilha>} />;
    corpo = (
      <div key={geracaoEscolhida.identificador} className="surge mx-auto max-w-[560px]">
        <h2 className="text-[24px] font-normal leading-tight">{geracaoEscolhida.nome}</h2>
        <p className="mt-2 text-[14px] text-etiqueta">{formatarDataCurta(geracaoEscolhida.iniciada_em)}</p>
        <div className="mt-8 flex flex-col gap-2.5">
          {formatos.length === 0 && <p className="text-[15px] text-etiqueta">Nada gerado nesta Saída.</p>}
          {formatos.map((formato) => (
            <Botao
              key={formato}
              variante="escuro"
              tamanho="grande"
              onClick={() => abrirGeracao(geracaoEscolhida, formato)}
            >
              Abrir {rotuloFormato(formato).toLowerCase()}
            </Botao>
          ))}
        </div>
      </div>
    );
  }

  return (
    <Divisao
      esquerda={esquerda}
      direita={
        <>
          {topo}
          <CorpoDaPrevia>{corpo}</CorpoDaPrevia>
        </>
      }
    />
  );
}
