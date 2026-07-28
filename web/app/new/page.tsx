import { ArtDirection } from "@/components/ArtDirection";
import { WizardSteps } from "@/components/WizardSteps";

export default function NewStory() {
  return (
    <main style={{ margin: "-28px -36px 0" }}>
      <WizardSteps active={2} />
      <div style={{ padding: "0 36px 40px" }}>
        <ArtDirection />
      </div>
    </main>
  );
}
