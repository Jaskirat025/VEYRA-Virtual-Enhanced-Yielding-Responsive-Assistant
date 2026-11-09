import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { VeyraProvider } from "./lib/useVeyra";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <VeyraProvider>
      <App />
    </VeyraProvider>
  </React.StrictMode>,
);
