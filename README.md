# PSYCHE Framework - Client Simulation

**Patient Simulation for Yielding psyCHiatric assessment conversational agent Evaluation**

A research platform for evaluating psychiatric assessment conversational agents (PACAs) through construct-grounded simulation and evaluation.

## Quick Start

1. **Dev container auto-starts** - Streamlit runs on port 8501 after container initialization
2. **Configure secrets** - Ensure Firebase credentials in `.streamlit/secrets.toml`
3. **Access UI** - Navigate to `http://localhost:8501`

## Documentation

📖 **For comprehensive development guide, see [.github/copilot-instructions.md](.github/copilot-instructions.md)**

This includes:
- Architecture overview (PSYCHE-SP, PACA, MFC system)
- Project structure and key files
- Development workflows (running experiments, creating pages)
- Memory management patterns (critical for Streamlit + LangChain)
- Expert validation workflows
- Testing and debugging
- Common gotchas and solutions

## Tech Stack

- **Frontend**: Streamlit
- **LLM Framework**: LangChain
- **Models**: OpenAI (GPT-4o, GPT-4o-mini, GPT-5.1), Anthropic (Claude-3-5-Sonnet, Claude-3-Haiku)
- **Database**: Firebase Realtime Database
- **Analysis**: Pandas, Matplotlib, Seaborn, Scipy, Pingouin

## Research Context

Peer-reviewed research paper currently in revision stage. Framework enables:
- **Construct-grounded patient simulation** via Multi-faceted Construct (MFC)
- **Quantitative PACA evaluation** via PSYCHE SCORE (0-55 range)
- **Expert validation studies** for SP authenticity and PACA competence

**Target Disorders**: MDD, BD, PD, GAD, SAD, OCD, PTSD

## License

Research project - contact repository owner for usage permissions.
