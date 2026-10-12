// Se uma tela quebrar ao renderizar, o resto do app continua: o menu fica e a pessoa sai dali.
// Sem isto, um erro de renderização deixa a página inteira em branco.
import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface Estado {
  erro: Error | null;
}

export default class LimiteDeErro extends Component<Props, Estado> {
  state: Estado = { erro: null };

  static getDerivedStateFromError(erro: Error): Estado {
    return { erro };
  }

  componentDidCatch(erro: Error, informacao: ErrorInfo): void {
    console.error("Erro de renderização:", erro, informacao.componentStack);
  }

  render(): ReactNode {
    if (this.state.erro === null) return this.props.children;
    return (
      <div role="alert" className="m-5 rounded-xl border border-suno/45 bg-suno/10 px-4 py-3 text-sm">
        <p className="font-semibold text-[#ffb3ad]">Algo quebrou nesta tela.</p>
        <p className="mt-1 text-suave">{this.state.erro.message}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="mt-3 rounded-full border border-[#55555b] px-3.5 py-1 text-xs font-semibold hover:border-texto"
        >
          Recarregar
        </button>
      </div>
    );
  }
}
