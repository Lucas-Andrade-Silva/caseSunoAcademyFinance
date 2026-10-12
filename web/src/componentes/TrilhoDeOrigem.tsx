// Um trilho da guia Fontes: o cabeçalho da Origem (nome, ligada ou desligada, **Ver tudo**) e uma
// fileira horizontal de cartões de Ata. Origem indisponível vira uma linha tracejada "em breve".
import { useState } from "react";
import type { OrigemComAtas } from "../dados/cliente";
import CartaoDeAta from "./CartaoDeAta";

export default function TrilhoDeOrigem({
  origem,
  selecao,
  onAlternarSelecao,
  onAlternarOrigem,
  ocupado,
}: {
  origem: OrigemComAtas;
  selecao: readonly string[];
  onAlternarSelecao: (identificador: string) => void;
  onAlternarOrigem: (ativa: boolean) => void;
  ocupado: boolean;
}) {
  const [verTudo, definirVerTudo] = useState(false);

  if (!origem.disponivel) {
    return (
      <section className="mb-5 flex items-center gap-2.5 rounded-[13px] border border-dashed border-linha px-4 py-3.5 text-sm text-suave">
        <b className="text-texto">{origem.nome}</b>
        <span>{origem.aviso ?? "em breve"}</span>
      </section>
    );
  }

  return (
    <section className="mb-5" aria-label={origem.nome}>
      <div className="mb-2.5 flex items-center gap-2.5">
        <h2 className="text-sm font-bold">{origem.nome}</h2>
        <button
          type="button"
          disabled={ocupado}
          onClick={() => onAlternarOrigem(!origem.ativa)}
          aria-pressed={origem.ativa}
          title={origem.ativa ? "Clique para desligar" : "Clique para ligar"}
          className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-linha px-2 py-px text-[10.5px] text-suave hover:border-[#55555b] disabled:opacity-50"
        >
          <span className={`h-1.5 w-1.5 rounded-full ${origem.ativa ? "bg-ok" : "bg-[#5a5a60]"}`} />
          {origem.ativa ? "ligada" : "desligada"}
        </button>
        <span className="text-[11px] text-suave">
          {origem.atas.length} {origem.atas.length === 1 ? "item" : "itens"}
        </span>
        {origem.atas.length > 0 && (
          <button
            type="button"
            onClick={() => definirVerTudo((atual) => !atual)}
            className="ml-auto rounded-[14px] border border-linha px-3 py-0.5 text-[11px] font-semibold hover:border-[#55555b]"
          >
            {verTudo ? "Recolher" : "Ver tudo"}
          </button>
        )}
      </div>

      {origem.atas.length === 0 ? (
        <p className="rounded-[13px] border border-dashed border-linha px-4 py-3.5 text-[12.5px] text-suave">
          {origem.ativa
            ? "Nenhum item ainda. Clique em Atualizar fontes ou importe um documento."
            : "Desligada: não entra na sugestão da curadoria. Ligue e clique em Atualizar fontes para trazer itens."}
        </p>
      ) : (
        <div
          className={`flex gap-[11px] pb-2 ${verTudo ? "flex-wrap" : "overflow-x-auto"}`}
          role="list"
        >
          {origem.atas.map((ata) => (
            <div key={ata.identificador} role="listitem">
              <CartaoDeAta
                ata={ata}
                selecionada={selecao.includes(ata.identificador)}
                desligada={!origem.ativa}
                onAlternar={() => onAlternarSelecao(ata.identificador)}
              />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
