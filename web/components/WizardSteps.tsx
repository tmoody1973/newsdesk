/** The three-step header. Canary underlines the active step and appears in
 *  exactly two places in this product — here and the rail's active cell. */
const STEPS = ["Facts & Sources", "Art Direction", "Script Review"];

export function WizardSteps({ active }: { active: 1 | 2 | 3 }) {
  return (
    <div style={{ display: "flex", borderBottom: "2px solid var(--color-divider)" }}>
      {STEPS.map((label, i) => {
        const n = (i + 1) as 1 | 2 | 3;
        const on = n === active;
        return (
          <div
            key={label}
            style={{
              flex: 1,
              padding: "18px 36px 14px",
              color: on ? undefined : "var(--color-neutral-500)",
              borderBottom: on ? "4px solid #F2C744" : undefined,
              marginBottom: on ? -2 : undefined,
            }}
          >
            <span className="mono" style={{ fontSize: 11, color: on ? "var(--color-neutral-600)" : undefined }}>
              {n}
            </span>{" "}
            <span style={{ fontWeight: on ? 800 : 400, fontSize: 14 }}>{label}</span>
          </div>
        );
      })}
    </div>
  );
}
