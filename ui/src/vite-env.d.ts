/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_VEYRA_PORT?: string;
  readonly VITE_VEYRA_TOKEN?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
