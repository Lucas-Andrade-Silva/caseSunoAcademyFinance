// Leva um elemento à vista rolando só a área de rolagem que o contém. O `scrollIntoView` do
// navegador rola todos os ancestrais, inclusive o `<main>` do app (overflow hidden, com as vistas
// vizinhas deslocadas), e a tela inteira sairia do lugar.

const MARGEM_PX = 24;

export function mostrarNaRolagem(elemento: HTMLElement, suave: boolean): void {
  for (let pai = elemento.parentElement; pai; pai = pai.parentElement) {
    const { overflowY } = getComputedStyle(pai);
    if (overflowY !== "auto" && overflowY !== "scroll") continue;
    if (pai.scrollHeight <= pai.clientHeight) continue;

    const alvo = elemento.getBoundingClientRect();
    const area = pai.getBoundingClientRect();
    const folgaNoTopo = alvo.top - area.top;
    const excessoEmbaixo = alvo.bottom - area.bottom;

    let deslocamento = 0;
    if (folgaNoTopo < 0) deslocamento = folgaNoTopo - MARGEM_PX;
    // Embaixo, mostra o fim do elemento sem esconder o começo dele.
    else if (excessoEmbaixo > 0) deslocamento = Math.min(excessoEmbaixo + MARGEM_PX, folgaNoTopo - MARGEM_PX);

    if (deslocamento !== 0) pai.scrollBy({ top: deslocamento, behavior: suave ? "smooth" : "auto" });
    return;
  }
}
