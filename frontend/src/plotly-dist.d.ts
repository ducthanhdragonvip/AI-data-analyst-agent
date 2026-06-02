declare module "plotly.js/dist/plotly" {
  import type { Data, Layout } from "plotly.js";

  type PlotlyApi = {
    react: (
      element: HTMLElement,
      data: Data[],
      layout?: Partial<Layout>,
      config?: Record<string, unknown>
    ) => Promise<unknown>;
    purge: (element: HTMLElement) => void;
  };

  const Plotly: PlotlyApi;
  export default Plotly;
}
