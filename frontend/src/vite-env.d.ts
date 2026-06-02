/// <reference types="vite/client" />

declare module "react-plotly.js" {
  import type { Data, Layout } from "plotly.js";

  type PlotProps = {
    data: Data[];
    layout?: Partial<Layout>;
    useResizeHandler?: boolean;
    className?: string;
  };

  export default function Plot(props: PlotProps): JSX.Element;
}
