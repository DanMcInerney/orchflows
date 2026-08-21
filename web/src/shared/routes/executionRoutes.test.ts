import { describe, expect, it } from "vitest";

import {
  EXECUTION_ROUTE_PARENT,
  executionRunRoute,
  executionTicketRoute,
} from "./executionRoutes";

const location = (pathname: string, search = "") => ({
  pathname,
  search,
  hash: "",
});

describe("shared execution routes", () => {
  it("builds encoded native links for runs and tickets", () => {
    expect(executionRunRoute.build({ run: "run / one", fixture: "active now" })).toBe(
      "/runs/run%20%2F%20one?fixture=active+now",
    );
    expect(
      executionTicketRoute.build({
        run: "run / one",
        ticket: "ticket #2",
        fixture: "",
      }),
    ).toBe("/runs/run%20%2F%20one/tickets/ticket%20%232");
  });

  it("parses run and ticket descendants back to canonical coordinates", () => {
    expect(
      executionRunRoute.match(location("/runs/run%20%2F%20one", "?fixture=active+now")),
    ).toEqual({ run: "run / one", fixture: "active now" });
    expect(
      executionTicketRoute.match(
        location("/runs/run%20%2F%20one/tickets/ticket%20%232", "?fixture=proof"),
      ),
    ).toEqual({ run: "run / one", ticket: "ticket #2", fixture: "proof" });
  });

  it("rejects invalid or mismatched execution coordinates", () => {
    expect(executionRunRoute.match(location("/runs/bad%escape"))).toBeNull();
    expect(executionRunRoute.match(location("/runs/a/tickets/b"))).toBeNull();
    expect(executionTicketRoute.match(location("/runs/a/tickets/b/extra"))).toBeNull();
    expect(executionTicketRoute.match(location("/runs/a/tickets/bad%escape"))).toBeNull();
  });

  it("assigns execution descendants to the Now rail", () => {
    expect(EXECUTION_ROUTE_PARENT).toBe("now");
  });
});
