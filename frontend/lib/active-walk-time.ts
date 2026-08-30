export function formatElapsed(seconds: number): string {
  const minutes = Math.floor(seconds / 60); const remainder = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

export function durationWarning(elapsedSeconds: number, limitMinutes: number): boolean {
  return limitMinutes === 0 || elapsedSeconds >= limitMinutes * 60;
}
