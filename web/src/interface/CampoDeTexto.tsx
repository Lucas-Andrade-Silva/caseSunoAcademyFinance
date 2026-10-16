// Um campo de texto de várias linhas no tom do app: rótulo pequeno em cima, fundo escuro, borda que
// acende no foco. Usado pelas edições de quadro e de cena.
import { useId, type TextareaHTMLAttributes } from "react";

interface Propriedades extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "onChange"> {
  rotulo: string;
  valor: string;
  aoMudar: (valor: string) => void;
}

export default function CampoDeTexto({ rotulo, valor, aoMudar, rows = 3, className = "", ...resto }: Propriedades) {
  const id = useId();
  return (
    <div>
      <label htmlFor={id} className="text-[12px] font-medium uppercase tracking-[0.02em] text-etiqueta">
        {rotulo}
      </label>
      <textarea
        id={id}
        rows={rows}
        value={valor}
        onChange={(evento) => aoMudar(evento.target.value)}
        className={`mt-1.5 block w-full resize-y rounded-lg border border-[#3d3d3d] bg-fundo px-4 py-3 text-[15px] leading-relaxed text-claro outline-none transition-colors duration-150 focus:border-white ${className}`}
        {...resto}
      />
    </div>
  );
}
