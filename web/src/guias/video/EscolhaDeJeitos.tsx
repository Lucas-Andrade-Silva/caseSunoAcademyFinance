// A escolha do jeito do vídeo, na linguagem da escolha de fontes do editor de referência: cartões
// quadrados, o escolhido em branco com texto escuro. Dois grupos que combinam (tom e ritmo); apertar
// o cartão escolhido de novo tira a escolha.
import { FaceGrinning, FaceNeutral, FaceSlightlySmiling, Rabbit, Turtle } from "lucide-react";
import { Rotulo, TituloDeSecao } from "../../interface/Divisao";
import { com } from "../../interface/Icones";
import {
  CLIMAS,
  RITMOS,
  type ClimaDoNarrador,
  type OpcaoDeJeito,
  type RitmoDoNarrador,
} from "./jeitos";

type IconeDoCartao = ReturnType<typeof com>;

const ICONE_DO_CLIMA: Record<ClimaDoNarrador, IconeDoCartao> = {
  descontraido: com(FaceSlightlySmiling),
  serio: com(FaceNeutral),
  engracado: com(FaceGrinning),
};

const ICONE_DO_RITMO: Record<RitmoDoNarrador, IconeDoCartao> = {
  devagar: com(Turtle),
  rapido: com(Rabbit),
};

interface GrupoProps<V extends string> {
  rotulo: string;
  opcoes: readonly OpcaoDeJeito<V>[];
  icones: Record<V, IconeDoCartao>;
  valor: V | null;
  onMudar: (valor: V | null) => void;
}

function Grupo<V extends string>({ rotulo, opcoes, icones, valor, onMudar }: GrupoProps<V>) {
  return (
    <div>
      <Rotulo>{rotulo}</Rotulo>
      <div role="group" aria-label={rotulo} className="mt-3 grid grid-cols-3 gap-4">
        {opcoes.map((opcao) => {
          const escolhida = opcao.valor === valor;
          const Icone: IconeDoCartao = icones[opcao.valor];
          return (
            <button
              key={opcao.valor}
              type="button"
              aria-pressed={escolhida}
              onClick={() => onMudar(escolhida ? null : opcao.valor)}
              className={`flex h-[98px] flex-col items-center justify-center gap-2.5 rounded-lg px-1 text-center transition-colors duration-150 ${
                escolhida ? "bg-claro text-ilha" : "bg-superficie text-texto hover:bg-superficie-alta"
              }`}
            >
              <Icone size={28} />
              <span className="text-[14px] leading-tight">{opcao.rotulo}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

interface Propriedades {
  clima: ClimaDoNarrador | null;
  ritmo: RitmoDoNarrador | null;
  onClima: (valor: ClimaDoNarrador | null) => void;
  onRitmo: (valor: RitmoDoNarrador | null) => void;
}

export default function EscolhaDeJeitos({ clima, ritmo, onClima, onRitmo }: Propriedades) {
  return (
    <div>
      <TituloDeSecao>Estilo</TituloDeSecao>
      <div className="mt-6 flex flex-col gap-8">
        <Grupo rotulo="Tom" opcoes={CLIMAS} icones={ICONE_DO_CLIMA} valor={clima} onMudar={onClima} />
        <Grupo rotulo="Ritmo" opcoes={RITMOS} icones={ICONE_DO_RITMO} valor={ritmo} onMudar={onRitmo} />
      </div>
    </div>
  );
}
