// O popup de "Atualizar fontes" quando a consulta acha mais de 2 notícias novas nos últimos 30
// dias: mostra a quantidade e deixa escolher o período a baixar. À esquerda o período (atalhos e
// datas) e o botão; à direita, quantas há por origem e por dia, com o período marcado.
import { useMemo, useState } from "react";
import type { EstadoDaAtualizacao, OrigemComAtas } from "../../dados/cliente";
import Botao from "../../interface/Botao";
import { IconeGirando } from "../../interface/Icones";
import Modal from "../../interface/Modal";
import { Quadrado } from "../../interface/Linha";
import { Pilulas } from "../../interface/Pilulas";
import { caraDaOrigem } from "./origens";
import { MAXIMO_POR_DOWNLOAD, diaEMes, inicioDoAtalho, noPeriodo, porDia, porOrigem } from "./periodo";

type Atalho = "7" | "15" | "30" | "outro";

const CAMPO =
  "h-[56px] w-full rounded-lg bg-superficie px-5 text-[17px] text-texto outline-none focus:ring-1 focus:ring-claro/60 [color-scheme:dark]";

export default function FiltrarPeriodo({
  estado,
  origens,
  enviando,
  erro,
  onBaixar,
  onCancelar,
}: {
  estado: EstadoDaAtualizacao;
  origens: readonly OrigemComAtas[];
  enviando: boolean;
  erro: string | null;
  onBaixar: (de: string, ate: string) => void;
  onCancelar: () => void;
}) {
  const disponiveis = estado.disponiveis ?? [];
  const desde = estado.desde ?? disponiveis.at(-1)?.data ?? "";
  const ate = estado.ate ?? disponiveis[0]?.data ?? "";
  const [de, definirDe] = useState(desde);
  const [fim, definirFim] = useState(ate);
  const [atalho, definirAtalho] = useState<Atalho>("30");

  const escolhidas = useMemo(() => noPeriodo(disponiveis, de, fim), [disponiveis, de, fim]);
  const dias = useMemo(() => porDia(disponiveis, desde, ate), [disponiveis, desde, ate]);
  const maximoDoDia = Math.max(1, ...dias.map((d) => d.total));
  const nomes = new Map(origens.map((o) => [o.id, o.nome]));
  const invertido = de > fim;
  const demais = escolhidas.length > MAXIMO_POR_DOWNLOAD;
  const pode = escolhidas.length > 0 && !invertido && !demais && !enviando;

  function escolherAtalho(valor: Atalho) {
    definirAtalho(valor);
    if (valor === "outro") return;
    definirDe(inicioDoAtalho(Number(valor), desde, ate));
    definirFim(ate);
  }

  const esquerda = (
    <div className="flex max-w-[489px] flex-col">
      <h2 className="text-[30px] font-normal leading-[1.3]">
        {disponiveis.length} notícias novas nos últimos {estado.janela_dias ?? 30} dias.
      </h2>
      <p className="mt-3 text-[20px] leading-snug text-apagado">Qual período você quer baixar?</p>

      <div className="mt-8">
        <Pilulas<Atalho>
          rotuloAcessivel="Período"
          valor={atalho}
          onMudar={escolherAtalho}
          opcoes={[
            { valor: "7", rotulo: "7 dias" },
            { valor: "15", rotulo: "15 dias" },
            { valor: "30", rotulo: "30 dias" },
            { valor: "outro", rotulo: "Datas" },
          ]}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2.5">
        <label className="sr-only" htmlFor="periodo-de">
          De
        </label>
        <input
          id="periodo-de"
          type="date"
          min={desde}
          max={ate}
          value={de}
          onChange={(evento) => {
            definirDe(evento.target.value);
            definirAtalho("outro");
          }}
          className={CAMPO}
        />
        <label className="sr-only" htmlFor="periodo-ate">
          Até
        </label>
        <input
          id="periodo-ate"
          type="date"
          min={desde}
          max={ate}
          value={fim}
          onChange={(evento) => {
            definirFim(evento.target.value);
            definirAtalho("outro");
          }}
          className={CAMPO}
        />
      </div>

      {(erro || invertido || demais) && (
        <p role="alert" className="mt-4 text-[14px] leading-snug text-coral-claro">
          {erro ??
            (invertido
              ? "A data inicial vem depois da final."
              : `No máximo ${MAXIMO_POR_DOWNLOAD} por vez. Escolha um período menor.`)}
        </p>
      )}

      <div className="mt-6 flex flex-col gap-2.5">
        <Botao
          variante="claro"
          tamanho="grande"
          disabled={!pode}
          icone={enviando ? <IconeGirando className="animate-spin" size={20} /> : undefined}
          onClick={() => onBaixar(de, fim)}
        >
          {enviando ? "Baixando" : `Baixar ${escolhidas.length}`}
        </Botao>
        <Botao variante="escuro" tamanho="grande" disabled={enviando} onClick={onCancelar}>
          Cancelar
        </Botao>
      </div>
    </div>
  );

  const direita = (
    <div className="flex flex-col gap-8 p-6 lg:p-[50px]">
      <div>
        <div className="flex h-[120px] items-end gap-[3px]" aria-hidden="true">
          {dias.map((dia) => {
            const dentro = dia.data >= de && dia.data <= fim;
            return (
              <span
                key={dia.data}
                title={`${diaEMes(dia.data)}: ${dia.total}`}
                className={`flex-1 rounded-sm transition-colors duration-150 ${dentro ? "bg-claro" : "bg-superficie-alta"}`}
                style={{ height: `${Math.max(dia.total === 0 ? 3 : 10, (dia.total / maximoDoDia) * 100)}%` }}
              />
            );
          })}
        </div>
        <div className="mt-2 flex justify-between text-[13px] tabular-nums text-etiqueta">
          <span>{diaEMes(desde)}</span>
          <span>{diaEMes(ate)}</span>
        </div>
      </div>

      <ul className="flex flex-col gap-2.5">
        {porOrigem(escolhidas).map(({ origem, total }) => {
          const cara = caraDaOrigem(origem);
          return (
            <li key={origem} className="flex h-[70px] items-center gap-4 rounded-lg bg-superficie px-[21px]">
              <Quadrado cor={cara.cor}>{cara.icone(20)}</Quadrado>
              <span className="min-w-0 flex-1 truncate text-[17px]">{nomes.get(origem) ?? origem}</span>
              <span className="text-[17px] tabular-nums text-claro">{total}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );

  return <Modal rotuloAcessivel="Período das notícias" esquerda={esquerda} direita={direita} onFechar={onCancelar} />;
}
