Adding a new engineer personality

To add a new Engineer personality, create a new module under backend/ai/personalities/ that exports a PERSONALITY object.

Steps:
1. Create a file: backend/ai/personalities/<id>.py
2. Import the common data model and construct a PERSONALITY instance:

from ai.personality import EngineerPersonality

PERSONALITY = EngineerPersonality(
    id="<id>",
    name="Display Name",
    description="Short description",
    style_instructions="Concise guidance on communication style",
)

3. The new module is automatically picked up by the registry in backend/ai/personalities/__init__.py — add an import there to register it.

4. Restart the backend (if running). The frontend will list registered personalities automatically.

Notes:
- Capture communication style rather than imitating specific individuals.
- Keep messages short; provide high-level tone/guidance in style_instructions.
