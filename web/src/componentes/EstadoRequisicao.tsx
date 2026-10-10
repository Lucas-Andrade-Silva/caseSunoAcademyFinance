// Estados de carregando/erro reutilizados em toda página — nada quebra sem rede ou sem dado.
export function Carregando({ rotulo = "Carregando…" }: { rotulo?: string }) {
  return (
    <div className="flex items-center gap-2 px-5 py-8 text-sm text-suave">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-linha border-t-texto" />
      {rotulo}
    </div>
  );
}

export function MensagemErro({ erro }: { erro: Error }) {
  return (
    <div className="m-5 rounded-xl border border-suno/45 bg-suno/10 px-4 py-3 text-sm text-[#ffb3ad]">
      Não foi possível carregar: {erro.message}
    </div>
  );
}
