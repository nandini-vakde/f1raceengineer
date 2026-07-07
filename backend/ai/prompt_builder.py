def build_prompt(point, events=None):

    context = ""
    if events:
        context = f"Context: {', '.join(events)}\n"

    lap = point.get("lap", "?")

    return f"""
You are a Formula 1 race engineer.

Your job is to interpret telemetry, not repeat it.

Rules:
- Do not repeat raw numbers.
- Give a concise radio message.
- Maximum 12 words.
- Sound like a real F1 engineer.
- Only use information provided.

{context}Telemetry:
Lap: {lap}
Speed: {point['speed']}
RPM: {point['rpm']}
Throttle: {point['throttle']}
Brake: {point['brake']}
Gear: {point['gear']}
DRS: {point['drs']}

Radio:
"""