import resolve from "@rollup/plugin-node-resolve";
import commonjs from "@rollup/plugin-commonjs";
import typescript from "@rollup/plugin-typescript";

export default {
  input: "src/index.tsx",
  output: {
    file: "dist/index.js",
    format: "iife",
    exports: "default",
    globals: {
      react: "SP_REACT",
      "react-dom": "SP_REACTDOM",
      "decky-frontend-lib": "DFL"
    }
  },
  external: ["decky-frontend-lib", "react", "react-dom"],
  context: "window",
  plugins: [resolve(), commonjs(), typescript()]
};
