import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "@fontsource-variable/fredoka";
import "@fontsource-variable/nunito";
import "./estilos.css";
import "./personal.css"; // #432: estilo del prototipo del personal

createRoot(document.getElementById("raiz")!).render(<StrictMode><App /></StrictMode>);
