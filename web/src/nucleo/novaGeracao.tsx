// O "+" de nova geração ao lado do título de cada guia que gera. Quem sabe abrir o popup é o
// `FluxoDaGuia`; o título, que mora dentro da guia, só pede por este contexto.
import { createContext, useContext } from "react";

export const ContextoDaNovaGeracao = createContext<(() => void) | null>(null);

/** A função que abre o popup de nova geração; `null` fora de uma guia que gera. */
export const usarNovaGeracao = () => useContext(ContextoDaNovaGeracao);
