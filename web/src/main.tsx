import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./estilos/global.css";

const elemento = document.getElementById("raiz");
if (!elemento) {
  throw new Error("elemento #raiz não encontrado em index.html");
}

createRoot(elemento).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
