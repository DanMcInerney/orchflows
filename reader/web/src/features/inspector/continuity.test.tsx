import { cleanup, render } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import TicketInspector from "./Inspector";
import type { InspectorModel, TicketDetail } from "./model";

// The bundler resolves every `.css` request, with or without `?raw`, to the empty
// stub vitest substitutes for stylesheets, so the token contract is read off disk.
// The runner is the only Node-side surface here; application code stays strict.
declare const process: {
  cwd(): string;
  getBuiltinModule(id: "node:fs"): {
    existsSync(path: string): boolean;
    readFileSync(path: string, encoding: string): string;
  };
};

const files = process.getBuiltinModule("node:fs");

function stylesheet(underWeb: string): string {
  for (const base of [process.cwd(), `${process.cwd()}/web`]) {
    const candidate = `${base}/${underWeb}`;
    if (files.existsSync(candidate)) return files.readFileSync(candidate, "utf8");
  }
  throw new Error(`stylesheet not found from ${process.cwd()}: ${underWeb}`);
}

const inspectorCss = stylesheet("src/features/inspector/inspector.css");
const tokensCss = stylesheet("src/styles/tokens.css");

function model(overrides: Partial<TicketDetail> = {}): InspectorModel {
  const ticket = {
    id: "G1",
    status: "complete",
    executor: "orch-tdd",
    bound: "90m",
    claimed_at: "2026-01-01T00:00:00Z",
    claimed_by: "unit05-agent",
    depends_on: ["G0", "G2"],
    unreadable: false,
    readiness: {
      state: "complete",
      dependencies: [],
      explanation: "Every dependency is met and the report is recorded.",
      cause: "none",
      causal_chain: []
    },
    sections: { goal: "Hold the drill level in one design language." },
    report: "The recorded report.",
    pack: "orch-design-pack",
    history: [],
    raw: "",
    ...overrides
  };
  return { run: null, ticket } as InspectorModel;
}

function route(fixture: string, ticket = "G1") {
  return { run: "run-gamma", ticket, fixture };
}

const ready = (value: InspectorModel) => ({ status: "ready", model: value, error: null } as const);

function open(value: InspectorModel, fixture: string, search: string, ticket = "G1") {
  window.history.replaceState({}, "", `/runs/run-gamma/tickets/${ticket}${search}`);
  return render(<TicketInspector state={ready(value)} route={route(fixture, ticket)} />).container;
}

function text(node: Element | null | undefined): string {
  return (node?.textContent ?? "").trim();
}

const declarations = (css: string): Array<[string, string]> =>
  Array.from(css.matchAll(/([a-z-]+)\s*:\s*([^;{}]+);/g)).map(
    (match) => [match[1], match[2].trim()] as [string, string]
  );

afterEach(() => {
  cleanup();
  window.history.replaceState({}, "", "/");
});

describe("ticket detail continuity with the workflows exemplar", () => {
  it("carries the hero grammar: eyebrow, display identity, lede, routing pills, and a stat grid", () => {
    const container = open(model(), "running-overview", "?fixture=running-overview");
    const hero = container.querySelector(".inspector-hero");
    expect(hero).not.toBeNull();
    expect(text(hero?.querySelector(".eyebrow"))).toBe("Inspector evidence");
    expect(text(hero?.querySelector("h1#ticket-title"))).toBe("G1");
    expect(text(hero?.querySelector(".inspector-lede"))).toBe("Every dependency is met and the report is recorded.");
    expect(Array.from(hero?.querySelectorAll(".inspector-identities span") ?? []).map(text))
      .toEqual(["orch-tdd", "orch-design-pack", "bound 90m"]);

    const stats = Array.from(hero?.querySelectorAll(".inspector-stats > div") ?? []).map((cell) => [
      text(cell.querySelector("dt")),
      text(cell.querySelector("dd"))
    ]);
    expect(stats).toEqual([["Sections", "1"], ["Depends", "2"], ["Friction", "0"], ["Events", "0"]]);
  });

  it("gives every manifest ticket state a hero lede that agrees with its own status", () => {
    const states: Array<[string, string, string, string]> = [
      ["running-overview", "G4", "running", "The assigned worker is executing this ticket within its bound."],
      ["report-recorded", "G1", "complete", "Every dependency is met and the report is recorded."],
      ["report-historical", "G1", "failed", "This ticket failed under the earlier section grammar; its recorded sections are shown as written."],
      ["friction-present", "G1", "complete", "Every dependency is met and the report is recorded."],
      ["history-unavailable", "G7", "attention", "The ticket is suspended and has no durable event projection."],
      ["raw-escaped", "A2", "running", "The worker holds the claim; only the inert ticket source is projected."]
    ];
    for (const [fixture, ticket, state, lede] of states) {
      const container = open({ run: null, ticket: null }, fixture, `?fixture=${fixture}`, ticket);
      expect(container.querySelector(".inspector-status")?.getAttribute("data-state"), fixture).toBe(state);
      expect(text(container.querySelector(".inspector-lede")), fixture).toBe(lede);
      if (state !== "complete") {
        expect(text(container.querySelector(".inspector-lede")), `${fixture} must not claim completion`)
          .not.toMatch(/complete/i);
      }
      cleanup();
    }
  });

  it("renders a recorded report as one inert body with nothing parsed out of it", () => {
    const container = open({ run: null, ticket: null }, "report-recorded", "?fixture=report-recorded&tab=report");
    const body = container.querySelector(".report-body");
    expect(body).not.toBeNull();
    expect(text(body)).toContain("Gate replayed at the tip");
    expect(container.querySelector(".report-section"), "no section rows accompany a current-grammar report").toBeNull();
    expect(container.querySelector(".report-era"), "no earlier-grammar note accompanies a current-grammar report").toBeNull();
  });

  it("keeps each historical section's name at the surface and its body verbatim beneath it", () => {
    const container = open({ run: null, ticket: null }, "report-historical", "?fixture=report-historical&tab=report");
    expect(text(container.querySelector(".report-era"))).toContain("earlier five-section grammar");
    const sections = Array.from(container.querySelectorAll(".report-section"));
    expect(sections.map((section) => text(section.querySelector("h3"))))
      .toEqual(["Result", "Verification", "Feedback", "Risks"]);
    const verification = sections[1]?.querySelector(".report-section__body");
    expect(text(verification)).toContain("| # | verdict | oracle | class | evidence |");
    expect(text(verification)).toContain("| 2 | FAIL | install.py --dry-run | deterministic | plan named 3 scripts, 4 expected |");
    expect(container.querySelector("[data-verdict]"), "no verdict is parsed out of recorded prose").toBeNull();
  });

  it("renders report section labels and phase facts in the shared row grammar", () => {
    const historical = open(model({
      report: "",
      sections: { goal: "Hold the drill level.", result: "The recorded result.", feedback: "[]" }
    }), "", "?tab=report");
    const names = Array.from(historical.querySelectorAll(".report-section h3")).map(text);
    expect(names).toEqual(["Result", "Feedback"]);
    expect(text(historical.querySelectorAll(".report-section__body")[0])).toBe("The recorded result.");
    cleanup();

    const overview = open(model(), "", "?tab=overview");
    const facts = Array.from(overview.querySelectorAll(".inspector-card--phase .fact-rows > div"));
    expect(facts.map((row) => text(row.querySelector("dt")))).toEqual(["Cause", "Claim"]);
    expect(text(facts[0]?.querySelector("dd"))).toBe("none");
    expect(text(facts[1]?.querySelector("dd"))).toBe("unit05-agent · 2026-01-01T00:00:00Z");
  });

  it("holds every history event's agent identity at the row surface and its detail behind disclosure", () => {
    const container = open(model({
      history: [
        { ts: "2026-08-01T00:00:00Z", event: "claimed", agent: "unit05-agent", detail: "Claim recorded in the state sink." },
        { ts: "2026-08-01T01:00:00Z", event: "closed", agent: "unit05-agent", detail: "" }
      ]
    }), "", "?tab=history");

    const rows = Array.from(container.querySelectorAll(".history-row"));
    expect(rows).toHaveLength(2);
    expect(rows.map((row) => text(row.querySelector(".history-row__agent")))).toEqual(["unit05-agent", "unit05-agent"]);
    expect(rows.map((row) => text(row.querySelector("strong")))).toEqual(["claimed", "closed"]);
    expect(text(container.querySelector(".panel-heading"))).toContain("One agent identity");

    const first = rows[0]?.querySelector("details.disclosure");
    expect(text(first?.querySelector("summary"))).toBe("Durable detail");
    expect(text(first)).toContain("Claim recorded in the state sink.");
    expect(rows[1]?.querySelector("details")).toBeNull();
    expect(text(rows[1]?.querySelector(".history-row__detail--empty"))).toBe("No durable detail recorded.");
  });

  it("puts the friction observation at the row surface and its expectation behind disclosure", () => {
    const container = open(model(), "friction-present", "?fixture=friction-present&tab=friction");
    const row = container.querySelector(".friction-row");
    expect(text(row?.querySelector(".friction-row__headline strong")))
      .toBe("A deterministic oracle returned a failing verdict.");
    expect(row?.querySelector(".friction-row__headline")?.closest("details")).toBeNull();
    const disclosure = row?.querySelector("details.disclosure");
    expect(text(disclosure?.querySelector("summary"))).toBe("Expectation and host");
    expect(text(disclosure)).toContain("Every named criterion to carry verified evidence.");
    expect(container.querySelector(".friction-record"), "no cross-feature class reuse").toBeNull();
  });

  it("traces every sampled rendered value to a tokens.css token on its scale", () => {
    const scale = new Set(Array.from(tokensCss.matchAll(/(--[a-z0-9-]+)\s*:/g)).map((match) => match[1]));
    expect(scale.size).toBeGreaterThan(0);

    expect(inspectorCss, "no literal colour escapes the token scale").not.toMatch(/#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/);
    for (const name of new Set(Array.from(inspectorCss.matchAll(/var\((--[a-z0-9-]+)\)/g)).map((match) => match[1]))) {
      expect(scale.has(name), `${name} is declared in tokens.css`).toBe(true);
    }

    const spacing = /^(padding|margin|gap|row-gap|column-gap)(-(top|right|bottom|left|inline|block))?$/;
    for (const [property, value] of declarations(inspectorCss)) {
      if (property === "font-size") {
        expect(value, "font sizes land on the type scale").toMatch(/^var\(--type-[a-z0-9-]+\)$/);
      }
      if (property === "font") {
        expect(value, "font shorthands land on the type scale").toContain("var(--type-");
      }
      if (property === "border-radius") {
        expect(value, "radii land on the radius scale").toMatch(/^(999px|var\(--radius-[a-z0-9-]+\))$/);
      }
      if (spacing.test(property)) {
        for (const part of value.split(/\s+(?![^(]*\))/)) {
          expect(part, `${property} lands on the space scale`).toMatch(/^(0|auto|2px|3px|var\(--space-[0-9]+\))$/);
        }
      }
    }
  });

  it("reuses the exemplar's panel container and row hover surface rather than a parallel language", () => {
    expect(inspectorCss).toContain(".inspector-card { min-width: 0; overflow: hidden; border: 1px solid var(--border-subtle); border-radius: var(--radius-panel); background: var(--surface-1); }");
    for (const row of [".report-section", ".artifact-row", ".friction-row", ".history-row"]) {
      expect(inspectorCss, `${row} carries the catalog row hover surface`)
        .toContain(`${row}:hover { background: var(--surface-2); }`);
    }
    expect(inspectorCss).toContain("font: 760 var(--type-display)/1.1 var(--font-mono)");
    expect(inspectorCss).toContain("font: 720 var(--type-metric)/1 var(--font-mono)");
  });
});
