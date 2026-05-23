export function shouldShowHint(profile) {
  return profile.wrongStreak >= 3;
}

export function shouldForceAdvance(profile) {
  return profile.wrongStreak >= 5;
}
