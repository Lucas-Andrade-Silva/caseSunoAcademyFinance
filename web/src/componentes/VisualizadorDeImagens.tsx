// Tela cheia para conferir os slides de um Carrossel: setas, teclado (← → Esc), miniaturas e
// baixar o slide aberto. Os slides são PNG 1080×1350 (4:5), o formato do feed.
import { useEffect } from "react";

interface ImagemDoVisualizador {
  url: string;
  rotulo: string;
  nomeDoArquivo: string;
}

const BOTAO =
  "rounded-full border border-[#55555b] bg-black/50 px-4 py-2 text-xs font-semibold text-texto hover:border-texto disabled:opacity-30";

export default function VisualizadorDeImagens({
  imagens,
  indice,
  onMudar,
  onFechar,
}: {
  imagens: ImagemDoVisualizador[];
  indice: number;
  onMudar: (indice: number) => void;
  onFechar: () => void;
}) {
  const total = imagens.length;
  const atual = imagens[indice];

  useEffect(() => {
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === "Escape") onFechar();
      if (evento.key === "ArrowRight") onMudar(Math.min(indice + 1, total - 1));
      if (evento.key === "ArrowLeft") onMudar(Math.max(indice - 1, 0));
    }
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [indice, total, onMudar, onFechar]);

  if (!atual) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={atual.rotulo}
      className="fixed inset-0 z-50 flex flex-col bg-black/90 p-4"
      onClick={onFechar}
    >
      <div
        className="flex items-center gap-3 pb-3"
        onClick={(e) => e.stopPropagation()}
      >
        <b className="text-sm">{atual.rotulo}</b>
        <div className="flex-1" />
        <a href={atual.url} download={atual.nomeDoArquivo} className={BOTAO}>
          Baixar este slide
        </a>
        <button
          type="button"
          onClick={onFechar}
          className={BOTAO}
          aria-label="Fechar"
        >
          Fechar ✕
        </button>
      </div>

      <div className="flex min-h-0 flex-1 items-center justify-center gap-3">
        <button
          type="button"
          aria-label="Slide anterior"
          disabled={indice === 0}
          onClick={(e) => {
            e.stopPropagation();
            onMudar(indice - 1);
          }}
          className={BOTAO}
        >
          ‹
        </button>
        <img
          src={atual.url}
          alt={atual.rotulo}
          onClick={(e) => e.stopPropagation()}
          className="max-h-full max-w-[calc(100%-8rem)] rounded-lg border border-linha object-contain"
        />
        <button
          type="button"
          aria-label="Próximo slide"
          disabled={indice === total - 1}
          onClick={(e) => {
            e.stopPropagation();
            onMudar(indice + 1);
          }}
          className={BOTAO}
        >
          ›
        </button>
      </div>

      <div
        className="flex justify-center gap-2 overflow-x-auto pt-3"
        onClick={(e) => e.stopPropagation()}
      >
        {imagens.map((imagem, i) => (
          <button
            key={imagem.url}
            type="button"
            onClick={() => onMudar(i)}
            aria-label={imagem.rotulo}
            aria-current={i === indice}
            className={`h-16 shrink-0 overflow-hidden rounded-md border ${
              i === indice
                ? "border-suno"
                : "border-linha opacity-70 hover:opacity-100"
            }`}
          >
            <img src={imagem.url} alt="" className="h-full" />
          </button>
        ))}
      </div>
    </div>
  );
}
