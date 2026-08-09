const EVENT_TAGS = {
  DRS_ACTIVE: 'DRS',
  HIGH_SPEED: 'PACE',
  BRAKING_ZONE: 'BRAKE',
}

/** Map backend event codes to a short UI tag for the engineer feed. */
export function tagFromEvents(events) {
  if (!Array.isArray(events) || events.length === 0) return 'INFO'
  for (const event of events) {
    if (EVENT_TAGS[event]) return EVENT_TAGS[event]
  }
  return 'INFO'
}
