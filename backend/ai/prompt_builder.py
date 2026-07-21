def build_prompt(point, events=None, personality=None):

    context = ""
    if events:
        context = f"Context: {', '.join(events)}\n"

    # personality may be a dataclass instance or a dict from the registry
    style = ""
    persona_name = None
    if personality:
        persona_name = getattr(personality, "name", None) or personality.get("name") if isinstance(personality, dict) else None
        style_text = getattr(personality, "style_instructions", None) or (personality.get("style_instructions") if isinstance(personality, dict) else None)
        if style_text:
            style = f"Communication style: {style_text}\n"

    lap = point.get("lap", "?")

    return f"""
You are a Formula 1 race engineer.{f' Persona: {persona_name}' if persona_name else ''}

{style}Your job is to interpret telemetry, not repeat it.

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