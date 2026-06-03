from src.modules.ai.agents.analyst import run_analyst_llm


def run_report_agent(context: str, instructions: str | None = None) -> str:
    prompt = instructions or "Create a Markdown analyst report with summary, findings, caveats, and next questions."
    return run_analyst_llm(prompt, context)
