// A guia Saídas ("/saidas"): as Saídas registradas, cada uma com nome, fonte, estado e a
// mini-Matriz. O conteúdo só aparece ao abrir a Saída (spec do front, seção 4.3).
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listarExecucoes } from "../dados/cliente";
import { usarRequisicao } from "../ganchos/usarRequisicao";
import { Carregando, MensagemErro } from "../componentes/EstadoRequisicao";
import CartaoSaida from "../componentes/CartaoSaida";
import { LegendaMiniMatriz } from "../componentes/MiniMatriz";
import {
  contarAguardando,
  filtrarSaidas,
  maisRecentesPrimeiro,
  type FiltroDeStatus,
} from "../lib/matriz";

const FILTROS: ReadonlyArray<{ valor: FiltroDeStatus; rotulo: string }> = [
  { valor: "todas", rotulo: "Todas" },
  { valor: "aguardando_revisao", rotulo: "Aguardando revisão" },
  { valor: "concluida", rotulo: "Concluídas" },
  { valor: "em_geracao", rotulo: "Em geração" },
  { valor: "com_problema", rotulo: "Interrompidas" },
];

const EM_GERACAO = ["na_fila", "gerando"];
const ATUALIZAR_A_CADA_MS = 3000;

export default function Saidas() {
  const [recarga, recarregar] = useState(0);
  // Enquanto alguma Saída está sendo gerada, a lista se atualiza sozinha, sem piscar.
  const estado = usarRequisicao(listarExecucoes, [recarga], {
    atualizarACada: (dados) =>
      dados.some((saida) => EM_GERACAO.includes(saida.status)) ? ATUALIZAR_A_CADA_MS : null,
  });
  const [busca, definirBusca] = useState("");
  const [filtro, definirFiltro] = useState<FiltroDeStatus>("todas");

  const saidas = useMemo(() => (estado.situacao === "pronto" ? estado.dados : []), [estado]);
  const visiveis = useMemo(
    () => maisRecentesPrimeiro(filtrarSaidas(saidas, { busca, status: filtro })),
    [saidas, busca, filtro],
  );

  if (estado.situacao === "carregando") return <Carregando rotulo="Carregando Saídas…" />;
  if (estado.situacao === "erro") return <MensagemErro erro={estado.erro} />;

  if (saidas.length === 0) {
    return (
      <div className="px-5 py-4">
        <h1 className="text-[17px] font-bold">Saídas</h1>
        <p className="mt-3 text-sm text-suave">
          Nenhuma Saída registrada ainda. Gere a primeira na guia{" "}
          <Link to="/fontes" className="font-semibold text-suno hover:underline">
            Fontes
          </Link>
          .
        </p>
      </div>
    );
  }

  const aguardando = contarAguardando(saidas);

  return (
    <div className="px-5 py-4">
      <div className="mb-3 flex items-baseline gap-3">
        <h1 className="text-[17px] font-bold">Saídas</h1>
        <span className="text-sm text-suave">
          {saidas.length} {saidas.length === 1 ? "registrada" : "registradas"}
        </span>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={busca}
          onChange={(evento) => definirBusca(evento.target.value)}
          placeholder="Buscar pelo nome…"
          className="w-full max-w-xs rounded-[10px] border border-linha bg-cartao px-3 py-1.5 text-sm placeholder:text-suave"
        />
        {FILTROS.map((opcao) => (
          <button
            key={opcao.valor}
            type="button"
            onClick={() => definirFiltro(opcao.valor)}
            className={`rounded-[10px] border px-3 py-1.5 text-xs ${
              filtro === opcao.valor ? "border-suno bg-suno/15" : "border-linha"
            }`}
          >
            {opcao.rotulo}
            {opcao.valor === "aguardando_revisao" && aguardando > 0 && (
              <b className="ml-1 text-suno">{aguardando}</b>
            )}
          </button>
        ))}
      </div>

      {visiveis.length === 0 ? (
        <p className="text-sm text-suave">Nenhuma Saída com esse filtro.</p>
      ) : (
        <div className="grid gap-3.5 sm:grid-cols-2 xl:grid-cols-3">
          {visiveis.map((saida) => (
            <CartaoSaida
              key={saida.identificador}
              saida={saida}
              onAlterada={() => recarregar((atual) => atual + 1)}
            />
          ))}
        </div>
      )}

      <LegendaMiniMatriz />
    </div>
  );
}
