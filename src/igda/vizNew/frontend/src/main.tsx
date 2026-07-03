import { createRoot } from "react-dom/client";
import { DnaScene } from "./DnaScene";

export function mount(container: HTMLElement): () => void {
  const root = createRoot(container);
  root.render(<DnaScene />);
  return () => root.unmount();
}
