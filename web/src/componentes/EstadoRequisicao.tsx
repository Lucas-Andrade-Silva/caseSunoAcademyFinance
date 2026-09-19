// Estados de carregando/erro reutilizados em toda página — nada quebra sem rede ou sem dado.
export function Carregando({ rotulo = "Carregando…" }: { rotulo?: string }) {
  return (
    <div className="flex items-center gap-2 py-8 text-sm text-slate-500 dark:text-slate-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600 dark:border-slate-700 dark:border-t-slate-300" />
      {rotulo}
    </div>
  );
}

export function MensagemErro({ erro }: { erro: Error }) {
  return (
    <div className="rounded-lg border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-900 dark:border-rose-800 dark:bg-rose-950 dark:text-rose-100">
      Não foi possível carregar: {erro.message}
    </div>
  );
}
