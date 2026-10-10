// O nome de quem está revisando, guardado só neste navegador (não há login). Sem
// armazenamento (janela privada, dados bloqueados), o nome vale só para esta sessão.

const CHAVE = "suno.revisor";

export function lerRevisor(): string {
  try {
    return window.localStorage.getItem(CHAVE) ?? "";
  } catch {
    return "";
  }
}

export function guardarRevisor(nome: string): void {
  try {
    window.localStorage.setItem(CHAVE, nome);
  } catch {
    // sem armazenamento: o nome não persiste, e a decisão segue valendo
  }
}
