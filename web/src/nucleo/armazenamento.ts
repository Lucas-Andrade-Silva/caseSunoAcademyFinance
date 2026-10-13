// Leitura e escrita no navegador sem nunca derrubar a tela: modo privado, site data bloqueado ou
// cota cheia viram "sem armazenamento", e o app segue valendo só até recarregar.
// `sessao` morre ao fechar a aba; `local` sobrevive.

type Lugar = "sessao" | "local";

function pegar(lugar: Lugar): Storage | null {
  try {
    return lugar === "sessao" ? window.sessionStorage : window.localStorage;
  } catch {
    return null;
  }
}

export function ler<T>(lugar: Lugar, chave: string, padrao: T): T {
  try {
    const bruto = pegar(lugar)?.getItem(chave);
    return bruto == null ? padrao : (JSON.parse(bruto) as T);
  } catch {
    return padrao;
  }
}

export function gravar(lugar: Lugar, chave: string, valor: unknown): void {
  try {
    pegar(lugar)?.setItem(chave, JSON.stringify(valor));
  } catch {
    /* sem armazenamento: o valor vale só até recarregar */
  }
}

export function apagar(lugar: Lugar, chave: string): void {
  try {
    pegar(lugar)?.removeItem(chave);
  } catch {
    /* idem */
  }
}
