import { GitBranch } from "lucide-react";
import { executionTicketRoute } from "../../shared/routes/executionRoutes";
import { skillSequence, statusGlyph, type SkillContinuity, type SkillPhase, type SkillStep } from "./model";

const PHASE_WORD: Record<SkillPhase, string> = {
  ran: "already run",
  running: "running now",
  remaining: "still to run"
};

const CONTINUITY_WORD: Record<SkillContinuity, string> = {
  first: "first skill in this run",
  "same-subagent": "same subagent as the previous skill",
  "new-subagent": "new subagent",
  unclaimed: "unclaimed, so no subagent continuity is claimed"
};

const SEAM_GLYPH: Record<Exclude<SkillContinuity, "first">, string> = {
  "same-subagent": "→",
  "new-subagent": "⇥",
  unclaimed: "⋯"
};

const SEAM_LABEL: Record<Exclude<SkillContinuity, "first">, string> = {
  "same-subagent": "",
  "new-subagent": "new agent",
  unclaimed: "unclaimed"
};

function stepName(step: SkillStep): string {
  return `${step.skill}, ticket ${step.ticket.id}, ${PHASE_WORD[step.phase]}, ${CONTINUITY_WORD[step.continuity]}`;
}

export interface SkillSequenceProps {
  runId: string;
  fixture: string;
  tickets: SkillStep["ticket"][];
}

export function SkillSequence({ runId, fixture, tickets }: SkillSequenceProps) {
  const sequence = skillSequence(tickets);
  if (sequence.steps.length === 0) return null;
  const total = sequence.steps.length;

  return (
    <section className="run-skills" aria-labelledby="run-skills-heading" data-testid="run-skills">
      <header className="run-skills__heading">
        <div>
          <p className="run-map__eyebrow"><GitBranch aria-hidden="true" />Skills, in the order they ran</p>
          <h2 id="run-skills-heading">{sequence.ran} of {total} skills run</h2>
        </div>
        <dl className="run-skills__tally">
          <div><dt>Run</dt><dd>{sequence.ran}</dd></div>
          <div><dt>Running</dt><dd>{sequence.running}</dd></div>
          <div><dt>To run</dt><dd>{sequence.remaining}</dd></div>
        </dl>
      </header>

      <ol className="run-skills__track" aria-label={`Skill sequence for ${runId}`}>
        {sequence.steps.map((step) => (
          <li
            key={`${step.order}:${step.ticket.id}`}
            className="run-skills__step"
            data-phase={step.phase}
            data-continuity={step.continuity}
          >
            {step.continuity !== "first" && (
              <span className="run-skills__seam" data-continuity={step.continuity} aria-hidden="true">
                <i>{SEAM_GLYPH[step.continuity]}</i>
                {SEAM_LABEL[step.continuity] && <em>{SEAM_LABEL[step.continuity]}</em>}
              </span>
            )}
            <a
              className="run-skills__node"
              href={executionTicketRoute.build({ run: runId, ticket: step.ticket.id, fixture })}
              data-phase={step.phase}
              data-continuity={step.continuity}
              data-agent={step.agent}
              aria-label={stepName(step)}
            >
              <span className="run-skills__glyph" data-status={step.ticket.readiness.state} aria-hidden="true">
                {statusGlyph(step.ticket.readiness.state)}
              </span>
              <b>{step.skill}</b>
              <span className="run-skills__ticket">{step.ticket.id}</span>
              <span className="run-skills__agent">{step.agent || "unclaimed"}</span>
            </a>
          </li>
        ))}
      </ol>

      <footer className="run-skills__legend" aria-label="Skill sequence legend">
        <span data-phase="ran"><i aria-hidden="true" />run</span>
        <span data-phase="running"><i aria-hidden="true" />running now</span>
        <span data-phase="remaining"><i aria-hidden="true" />still to run</span>
        <span data-continuity="same-subagent"><i aria-hidden="true" />same subagent</span>
        <span data-continuity="new-subagent"><i aria-hidden="true" />new subagent</span>
      </footer>
    </section>
  );
}

export default SkillSequence;
