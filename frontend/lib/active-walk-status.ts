export type ActiveWalkStatus = {
  state: "available";
  heat_risk: { score: number; status: string; recommendation: string };
  surface_risk: { score: number; level: string; reason: string; surface: string };
  recommended_duration_minutes: number;
  reminders: string[];
  caution: string;
  disclaimer: string;
};

export type ActiveWalkUnavailableStatus = {
  state: "unavailable";
  unavailable_reason: string;
  heat_risk: null;
  surface_risk: null;
  recommended_duration_minutes: null;
  reminders: string[];
  caution: string;
  disclaimer: string;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/**
 * API generics disappear at runtime. Validate this safety-critical response
 * before the Active Walk screen renders nested risk fields.
 */
export function isActiveWalkStatus(value: unknown): value is ActiveWalkStatus {
  if (!isRecord(value) || !isRecord(value.heat_risk) || !isRecord(value.surface_risk)) return false;

  return (
    value.state === "available" &&
    isFiniteNumber(value.heat_risk.score) &&
    typeof value.heat_risk.status === "string" &&
    typeof value.heat_risk.recommendation === "string" &&
    isFiniteNumber(value.surface_risk.score) &&
    typeof value.surface_risk.level === "string" &&
    typeof value.surface_risk.reason === "string" &&
    typeof value.surface_risk.surface === "string" &&
    isFiniteNumber(value.recommended_duration_minutes) &&
    value.recommended_duration_minutes >= 0 &&
    Array.isArray(value.reminders) &&
    value.reminders.every((reminder) => typeof reminder === "string") &&
    typeof value.caution === "string" &&
    typeof value.disclaimer === "string"
  );
}

export function isActiveWalkUnavailableStatus(value: unknown): value is ActiveWalkUnavailableStatus {
  return (
    isRecord(value) &&
    value.state === "unavailable" &&
    typeof value.unavailable_reason === "string" &&
    value.heat_risk === null &&
    value.surface_risk === null &&
    value.recommended_duration_minutes === null &&
    Array.isArray(value.reminders) &&
    value.reminders.every((reminder) => typeof reminder === "string") &&
    typeof value.caution === "string" &&
    typeof value.disclaimer === "string"
  );
}
