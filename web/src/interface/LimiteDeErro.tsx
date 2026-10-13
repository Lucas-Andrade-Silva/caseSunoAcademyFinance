// Se uma vista quebrar ao renderizar, as outras e a barra lateral continuam: a pessoa sai dali.
// Sem isto, um erro de renderização deixa a página inteira em branco.
import { Component, type ErrorInfo, type ReactNode } from "react";
import Botao from "./Botao";

interface Propriedades {
  children: ReactNode;
}

interface Estado {
  erro: Error | null;
}

export default class LimiteDeErro extends Component<Propriedades, Estado> {
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
      <div role="alert" className="mx-auto flex max-w-[469px] flex-col gap-4 px-5 py-24">
        <p className="text-[24px] text-coral-claro">Algo quebrou nesta guia.</p>
        <p className="text-[15px] text-etiqueta">{this.state.erro.message}</p>
        <Botao tamanho="pequeno" onClick={() => this.setState({ erro: null })}>
          Tentar de novo
        </Botao>
      </div>
    );
  }
}
