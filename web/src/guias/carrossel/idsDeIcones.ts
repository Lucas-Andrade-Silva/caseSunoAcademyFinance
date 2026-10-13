// A lista dos 15 ícones do catálogo do vídeo, na ordem em que a escolha os mostra. Sem React: a
// leitura dos salvos e os testes usam sem puxar a biblioteca de ícones.
import type { IdDoIcone } from "./modelo";

export const IDS_DE_ICONES: readonly { id: IdDoIcone; rotulo: string }[] = [
  { id: "juros", rotulo: "Juros" },
  { id: "inflacao", rotulo: "Inflação" },
  { id: "grafico_alta", rotulo: "Alta" },
  { id: "grafico_queda", rotulo: "Queda" },
  { id: "grafico_estavel", rotulo: "Estável" },
  { id: "calendario", rotulo: "Calendário" },
  { id: "banco", rotulo: "Banco" },
  { id: "bolso", rotulo: "Bolso" },
  { id: "alerta", rotulo: "Alerta" },
  { id: "lupa", rotulo: "Lupa" },
  { id: "documento", rotulo: "Documento" },
  { id: "balanca", rotulo: "Balança" },
  { id: "relogio", rotulo: "Relógio" },
  { id: "pergunta", rotulo: "Pergunta" },
  { id: "check", rotulo: "Check" },
];

export const ICONES_VALIDOS: ReadonlySet<string> = new Set(IDS_DE_ICONES.map((icone) => icone.id));

export function rotuloDoIcone(id: IdDoIcone): string {
  return IDS_DE_ICONES.find((icone) => icone.id === id)?.rotulo ?? id;
}
