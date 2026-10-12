// Estados de carregando/erro reutilizados em toda página — nada quebra sem rede ou sem dado.
export function Carregando({ rotulo = "Carregando…" }: { rotulo?: string }) {
  return (
    <div className="flex items-center gap-2 px-5 py-8 text-sm text-suave">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-linha border-t-texto" />
      {rotulo}
    </div>
  );
}

/** `onTentarDeNovo` padrão recarrega a página: serve a qualquer tela, sem cada uma saber refazer. */
export function MensagemErro({
  erro,
  onTentarDeNovo = () => window.location.reload(),
}: {
  erro: Error;
  onTentarDeNovo?: () => void;
}) {
  return (
    <div
      role="alert"
      className="m-5 flex flex-wrap items-center gap-3 rounded-xl border border-suno/45 bg-suno/10 px-4 py-3 text-sm text-[#ffb3ad]"
    >
      <span className="min-w-0 flex-1">Não foi possível carregar: {erro.message}</span>
      <button
        type="button"
        onClick={onTentarDeNovo}
        className="rounded-full border border-[#55555b] px-3.5 py-1 text-xs font-semibold text-texto hover:border-texto"
      >
        Tentar de novo
      </button>
    </div>
  );
}
