import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@xyflow/react/dist/style.css";

import { ObserveApp } from "./ObserveApp";
import "./styles/tokens.css";
import "./styles.css";

const container = document.getElementById("root");
if (!container) throw new Error("application root is missing");

createRoot(container).render(
  <StrictMode>
    <ObserveApp />
  </StrictMode>
);
