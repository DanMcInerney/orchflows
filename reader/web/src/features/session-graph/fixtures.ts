import type { SessionDetail } from "./topology";

export function sessionFixture(session: SessionDetail | null, _identity: string): SessionDetail | null {
  return session;
}

export const fixtures = { session: sessionFixture };
