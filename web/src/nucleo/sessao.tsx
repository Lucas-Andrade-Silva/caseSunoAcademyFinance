// A sessão de cada guia de conteúdo (Texto, Carrossel, Vídeo): pede a geração ao servidor, acompanha
// o andamento, e guarda as Células prontas. Vive acima das guias, então a geração continua se a
// pessoa trocar de guia. O servidor gera um job por vez; um segundo pedido espera na fila.
//
// Fases: `vazia` (nada gerado: a guia abre o popup), `enviando`, `gerando`, `pronta`, `falhou`.
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useLocation } from "react-router-dom";
import {
  AUDIENCIAS,
  FORMATOS,
  criarSaida,
  mensagemDeFalha,
  obterAndamento,
  obterExecucao,
  type Andamento,
  type Audiencia,
  type Conteudo,
  type Destino,
  type Formato,
  type Laudo,
} from "../dados/cliente";
import { rotuloFormato } from "../texto/rotulos";
import { apagar, gravar, ler } from "./armazenamento";
import { usarConfiguracoes } from "./configuracoes";
import { guiaDoCaminho } from "./guias";
import { corpoDaSaida, motivoDeRecusa, type ExtrasDaGeracao } from "./pedido";
import { usarSelecao } from "./selecao";

export type FaseDaSessao = "vazia" | "enviando" | "gerando" | "pronta" | "falhou";

export interface CelulaPronta {
  audiencia: Audiencia;
  formato: Formato;
  conteudo: Conteudo;
  laudo: Laudo | null;
  destino: Destino;
}

interface EstadoDaSessao {
  fase: FaseDaSessao;
  execucaoId: string | null;
  nome: string;
  andamento: Andamento | null;
  erro: string | null;
  audiencias: Audiencia[];
  celulas: Partial<Record<Audiencia, CelulaPronta>>;
  /** A geração terminou e a pessoa ainda não olhou a guia. */
  naoVista: boolean;
}

export interface Sessao extends EstadoDaSessao {
  formato: Formato;
  /** Pede a geração das Audiências escolhidas, com as notícias guardadas na Ingestão. */
  iniciar: (audiencias: readonly Audiencia[], extras?: ExtrasDaGeracao) => Promise<void>;
  /** Carrega as Células deste Formato de uma Saída que já existe (o Histórico usa). */
  abrir: (execucaoId: string) => Promise<void>;
  /** Volta a `vazia`: a guia reabre o popup. */
  limpar: () => void;
}

const VAZIO: EstadoDaSessao = {
  fase: "vazia",
  execucaoId: null,
  nome: "",
  andamento: null,
  erro: null,
  audiencias: [],
  celulas: {},
  naoVista: false,
};

type Estados = Record<Formato, EstadoDaSessao>;

const INTERVALO_MS = 1500;
const chaveDoFormato = (formato: Formato) => `suno.sessao.${formato}`;

/** O que a aba tinha antes de recarregar: a Saída de cada guia, para retomar em `enviando`. */
function estadoInicial(): Estados {
  const retomada = (formato: Formato): EstadoDaSessao => {
    const guardada = ler<{ execucaoId?: string }>("sessao", chaveDoFormato(formato), {});
    return guardada.execucaoId
      ? { ...VAZIO, fase: "enviando", execucaoId: guardada.execucaoId }
      : VAZIO;
  };
  return {
    texto_analitico: retomada("texto_analitico"),
    carrossel: retomada("carrossel"),
    roteiro: retomada("roteiro"),
  };
}

/** O que a execução tem deste Formato, na ordem das Audiências. */
function celulasDoFormato(
  execucao: Awaited<ReturnType<typeof obterExecucao>>,
  formato: Formato,
): Partial<Record<Audiencia, CelulaPronta>> {
  const celulas: Partial<Record<Audiencia, CelulaPronta>> = {};
  for (const audiencia of AUDIENCIAS) {
    const historico = (execucao.celulas ?? []).find(
      (h) => h.audiencia === audiencia && h.formato === formato,
    );
    const ultima = historico?.tentativas?.at(-1);
    if (!historico || !ultima) continue;
    celulas[audiencia] = {
      audiencia,
      formato,
      conteudo: ultima.celula.conteudo,
      laudo: ultima.laudo ?? null,
      destino: historico.destino_final,
    };
  }
  return celulas;
}

const Contexto = createContext<Record<Formato, Sessao> | null>(null);

export function ProvedorDeSessoes({ children }: { children: ReactNode }) {
  const [estados, definirEstados] = useState<Estados>(estadoInicial);
  const { atasGuardadas } = usarSelecao();
  const { modo } = usarConfiguracoes();
  const { pathname } = useLocation();
  const ativa = guiaDoCaminho(pathname)?.formato ?? null;

  // O que a polling precisa ler sem reiniciar o temporizador a cada render.
  const estadosRef = useRef(estados);
  estadosRef.current = estados;
  const ativaRef = useRef(ativa);
  ativaRef.current = ativa;

  const mudar = useCallback((formato: Formato, parte: Partial<EstadoDaSessao>) => {
    definirEstados((atuais) => ({ ...atuais, [formato]: { ...atuais[formato], ...parte } }));
  }, []);

  const carregarCelulas = useCallback(
    async (formato: Formato, execucaoId: string, avisar = false) => {
      try {
        const execucao = await obterExecucao(execucaoId);
        const celulas = celulasDoFormato(execucao, formato);
        const audiencias = AUDIENCIAS.filter((a) => celulas[a] !== undefined);
        if (audiencias.length === 0) {
          // Nenhuma Célula saiu: quase sempre o provedor caiu. A frase diz isso, não "não tem".
          const caiu = (execucao.celulas ?? []).some(
            (h) => h.formato === formato && /provedor|HTTP 5\d\d|cota/i.test(h.falha ?? ""),
          );
          mudar(formato, {
            fase: "falhou",
            erro: caiu
              ? "Os modelos de IA não responderam agora (sobrecarga ou cota). Tente de novo em instantes."
              : `A geração terminou sem ${rotuloFormato(formato).toLowerCase()}. Tente de novo.`,
          });
          return;
        }
        mudar(formato, {
          fase: "pronta",
          execucaoId,
          nome: execucao.nome,
          audiencias,
          celulas,
          erro: null,
          // Só uma geração que terminou agora acende o ponto da guia; reabrir o que já existia não.
          naoVista: avisar && ativaRef.current !== formato,
        });
      } catch (falha: unknown) {
        mudar(formato, { fase: "falhou", erro: mensagemDeFalha(falha) });
      }
    },
    [mudar],
  );

  const consultar = useCallback(
    async (formato: Formato) => {
      const id = estadosRef.current[formato].execucaoId;
      if (!id) return;
      try {
        const andamento = await obterAndamento(id);
        if (estadosRef.current[formato].execucaoId !== id) return;
        if (andamento.estado === "concluida") {
          mudar(formato, { andamento });
          await carregarCelulas(formato, id, true);
        } else if (andamento.estado === "falhou" || andamento.estado === "interrompida") {
          mudar(formato, {
            andamento,
            fase: "falhou",
            erro:
              andamento.erro ??
              (andamento.estado === "interrompida"
                ? "A geração foi interrompida (o servidor reiniciou ou a cota acabou)."
                : "A geração falhou."),
          });
        } else {
          mudar(formato, { andamento });
        }
      } catch {
        /* erro de rede passageiro: a próxima volta tenta de novo */
      }
    },
    [carregarCelulas, mudar],
  );

  // Uma polling só para todas as sessões em geração.
  const gerando = FORMATOS.filter((f) => estados[f].fase === "gerando")
    .map((f) => `${f}:${estados[f].execucaoId}`)
    .join("|");
  useEffect(() => {
    if (gerando === "") return;
    const volta = () => {
      FORMATOS.forEach((formato) => {
        if (estadosRef.current[formato].fase === "gerando") void consultar(formato);
      });
    };
    volta();
    const temporizador = window.setInterval(volta, INTERVALO_MS);
    return () => window.clearInterval(temporizador);
  }, [gerando, consultar]);

  // Guarda o que a pessoa está vendo, para sobreviver a um recarregamento da página.
  useEffect(() => {
    FORMATOS.forEach((formato) => {
      const { execucaoId, fase } = estados[formato];
      if (execucaoId && (fase === "gerando" || fase === "pronta")) {
        gravar("sessao", chaveDoFormato(formato), { execucaoId });
      } else if (fase === "vazia") {
        apagar("sessao", chaveDoFormato(formato));
      }
    });
  }, [estados]);

  const retomar = useCallback(
    async (formato: Formato, execucaoId: string) => {
      mudar(formato, { ...VAZIO, fase: "enviando", execucaoId });
      try {
        const andamento = await obterAndamento(execucaoId);
        if (andamento.estado === "na_fila" || andamento.estado === "gerando") {
          mudar(formato, { fase: "gerando", andamento });
          return;
        }
      } catch {
        /* Saída antiga, sem `andamento.json`: vale o que está gravado */
      }
      await carregarCelulas(formato, execucaoId);
    },
    [carregarCelulas, mudar],
  );

  // Ao abrir o app, retoma o que estava na tela antes de recarregar.
  useEffect(() => {
    FORMATOS.forEach((formato) => {
      const { fase, execucaoId } = estadosRef.current[formato];
      if (fase === "enviando" && execucaoId) void retomar(formato, execucaoId);
    });
  }, [retomar]);

  // Olhar a guia apaga o ponto de "pronto".
  useEffect(() => {
    if (ativa && estados[ativa].naoVista) mudar(ativa, { naoVista: false });
  }, [ativa, estados, mudar]);

  const iniciar = useCallback(
    async (formato: Formato, audiencias: readonly Audiencia[], extras?: ExtrasDaGeracao) => {
      const motivo = motivoDeRecusa({ atas: atasGuardadas, modo, audiencias });
      if (motivo) {
        mudar(formato, { ...VAZIO, fase: "falhou", erro: motivo });
        return;
      }
      mudar(formato, { ...VAZIO, fase: "enviando", audiencias: [...audiencias] });
      try {
        const andamento = await criarSaida(
          corpoDaSaida({ formato, audiencias, atas: atasGuardadas, modo, extras }),
        );
        mudar(formato, {
          fase: "gerando",
          execucaoId: andamento.identificador,
          nome: andamento.nome,
          andamento,
          audiencias: [...audiencias],
        });
      } catch (falha: unknown) {
        mudar(formato, { fase: "falhou", erro: mensagemDeFalha(falha) });
      }
    },
    [atasGuardadas, modo, mudar],
  );

  const sessoes = useMemo(() => {
    const resultado = {} as Record<Formato, Sessao>;
    for (const formato of FORMATOS) {
      resultado[formato] = {
        ...estados[formato],
        formato,
        iniciar: (audiencias, extras) => iniciar(formato, audiencias, extras),
        abrir: (execucaoId) => retomar(formato, execucaoId),
        limpar: () => mudar(formato, VAZIO),
      };
    }
    return resultado;
  }, [estados, iniciar, retomar, mudar]);

  return <Contexto.Provider value={sessoes}>{children}</Contexto.Provider>;
}

export function usarSessao(formato: Formato): Sessao {
  const contexto = useContext(Contexto);
  if (contexto === null) throw new Error("usarSessao fora do ProvedorDeSessoes");
  return contexto[formato];
}

/** As três sessões de uma vez (a barra lateral e o Histórico usam). */
export function usarSessoes(): Record<Formato, Sessao> {
  const contexto = useContext(Contexto);
  if (contexto === null) throw new Error("usarSessoes fora do ProvedorDeSessoes");
  return contexto;
}
