# Client Simulation - Copilot Instructions

## Project Overview

This is a **psychiatric evaluation research platform** that simulates patient-clinician interactions using two AI agents:

- **SP (Simulated Patient)**: LLM-based agent that mimics psychiatric patients based on profiles and behavioral instructions
- **PACA (Psychiatric Assessment Conversational Agent)**: LLM-based clinician agent that conducts psychiatric interviews

The system generates conversations, produces structured psychiatric assessments ("constructs"), evaluates PACA performance against ground truth (SP constructs), and enables expert validation by psychiatrists.

## Core Architecture

### Three-Layer Agent System

1. **SP Agent** (`SP_utils.py`, `sp_construct_generator.py`)
   - Built with LangChain + ChatOpenAI/ChatAnthropic
   - Configured via: profile JSON, history narrative, behavioral instructions
   - Uses `InMemoryChatMessageHistory` for conversation state
   - Cached with `@st.cache_resource` to persist across Streamlit reruns

2. **PACA Agent** (`PACA_*_utils.py`, `paca_construct_generator.py`)
   - Multiple variants: `claude_basic`, `claude_guided`, `gpt_basic`, `gpt_guided`, `llama`
   - Each has initial greeting prompt hardcoded (e.g., "안녕하세요, 저는 정신과 의사...")
   - Generates psychiatric constructs by querying itself post-conversation

3. **Evaluator** (`evaluator.py`, `expert_validation_utils.py`)
   - Compares PACA construct vs SP construct (ground truth)
   - Uses **PSYCHE RUBRIC** - standardized psychiatric evaluation criteria
   - Three scoring methods: G-Eval (LLM-based), binary, ordinal/delta-based

### Data Storage: Firebase Realtime Database

**All data lives in Firebase** with sanitized keys (no `$#[].`):

```python
# Key patterns (see SP_utils.sanitize_key):
clients/<client_number>/profile_version6_0  # Underscores replace dots
clients/<client_number>/beh_dir_version6_0
clients/<client_number>/construct_paca_<client_num>_<exp_num>
clients/<client_number>/conversation_log_<client_num>_<exp_num>
expert_<sanitized_name>_<client_num>_<exp_num>  # Validation results
```

**Critical**: Version numbers like `6.0` → `version6_0` in Firebase paths (see `save_to_firebase`/`load_from_firebase` in `SP_utils.py`)

## PSYCHE RUBRIC - Central Evaluation Schema

Defined in `evaluator.py` and `expert_validation_utils.py`:

```python
PSYCHE_RUBRIC = {
    # Subjective (weight=1): G-Eval scoring
    "Chief complaint": {"type": "g-eval", "weight": 1},
    "Symptom name": {"type": "g-eval", "weight": 1},
    
    # Impulsivity (weight=5): Delta-based (high=2, moderate=1, low=0)
    "Suicidal ideation": {"type": "impulsivity", "weight": 5, ...},
    
    # Behavior (weight=2): Ordinal scales
    "Mood": {"type": "behavior", "weight": 2, 
             "values": {"depressed": 1, "dysphoric": 2, ...}},
}
```

**Key patterns**:
- Multiple "Symptom 1-N" entries → aggregated to single "Symptom name" for expert validation
- PACA constructs are **flat** (`{"Mood": "depressed"}`), SP constructs are **nested** (`{"Mental Status Examination": {"Mood": "depressed"}}`)
- `flatten_construct()` in `evaluator.py` normalizes both to flat structure

## Development Workflows

### Running Experiments

1. **Preset versions** at top of Experiment files:
   ```python
   profile_version = 6.0
   beh_dir_version = 6.0
   con_agent_version = 6.0
   paca_version = 3.0
   ```

2. **Agent creation pattern**:
   ```python
   sp_agent, sp_memory = create_conversational_agent(
       profile_version, beh_dir_version, client_number, system_prompt)
   paca_agent, paca_memory, version = create_paca_agent(paca_version)
   ```

3. **Conversation simulation**:
   ```python
   for speaker, message in simulate_conversation(paca_agent, sp_agent):
       # Yields ("PACA", msg) or ("SP", msg)
   ```

4. **Construct generation** (post-conversation):
   ```python
   # Query PACA agent about what it learned
   paca_construct = create_paca_construct(paca_agent)
   # Ground truth from SP's profile
   sp_construct = create_sp_construct(client_number, profile_version)
   ```

### Memory Management (Critical!)

**Problem**: Streamlit reruns recreate objects, breaking LangChain memory

**Solution pattern** (see `MEMORY_FIX_GUIDE.md`):
```python
@st.cache_resource  # Caches agents across reruns
def create_paca_agent(version):
    memory = InMemoryChatMessageHistory()
    # Return memory explicitly so it persists with agent
    return agent, memory, version

# In page:
if 'sp_memory' not in st.session_state:
    st.session_state.sp_memory = sp_memory  # Persist memory
```

### Streamlit Page Structure

- `Home.py`: Authentication (checks `st.secrets["participant"]`), Playwright setup
- `pages/01_experiment(BD|MDD|OCD)_<model>_<type>.py`: Experiment runners per disorder/model
- `pages/06_expert_validation.py`: Multi-stage wizard (intro → test → validation loop)

**Navigation pattern**:
```python
st.session_state.validation_stage = 'intro'  # State machine for multi-page flows
st.rerun()  # Trigger page refresh
```

### Expert Validation Workflow

`pages/06_expert_validation.py`:

1. **PRESET at top**: List of `(client_number, experiment_number)` tuples to validate
2. **Three stages**: `intro` → `test` → `validation`
3. **Scoring pattern**:
   ```python
   scoring_options = get_aggregated_scoring_options(construct_data)
   # Returns {category: [{element, options, paca_value}, ...]}
   
   # Expert picks from options, score auto-calculated:
   validation_result = create_validation_result(
       construct_data, expert_responses, (client_num, exp_num))
   ```

4. **Firebase save**:
   ```python
   save_validation_to_firebase(
       firebase_ref, expert_name, (client_num, exp_num), result)
   # Saves to: expert_<sanitized_name>_<client>_<exp>
   ```

## Common Patterns & Conventions

### Version Formatting
```python
# Display: 6.0, Firebase: version6_0
f"version{version:.1f}".replace(".", "_")
```

### Prompt Loading
```python
# From data/prompts/<type>_system_prompt/<type>_system_prompt_version<X>.txt
system_prompt, version = load_prompt_and_get_version("con-agent", 6.0)
# BD patients get special prompt:
load_prompt_and_get_version("con-agent", 6.0, "BD")
```

### Firebase Key Sanitization
```python
# Replace forbidden chars: $ # [ ] / .
sanitize_key("clients/6101/profile.version6.0")
# → "clients_6101_profile_version6_0"
```

### Construct Structure Normalization
```python
# SP: {"Present illness": {"symptom_1": {"name": "insomnia"}}}
# PACA: {"Symptom name": "insomnia"}
# Both → {"Symptom name": "insomnia"} via flatten_construct()
```

## Configuration & Secrets

`st.secrets` (Streamlit secrets.toml):
- `firebase`: Service account JSON for Firebase Admin SDK
- `firebase_database_url`: Realtime Database URL
- `participant`: List of allowed expert names
- API keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` (via environment/secrets)

## Testing & Debugging

**Check memory persistence**:
```python
st.write(f"Memory has {len(memory.messages)} messages")  # Should increment
```

**Validate Firebase saves**:
```python
# Test key sanitization matches actual Firebase structure
sanitize_key("my/path.name") == "my_path_name"
```

**Experiment number conflicts**:
```python
check_experiment_number_exists(firebase_ref, client_number, exp_number)
# Prevents overwriting existing experiments
```

## Known Gotchas

1. **Version dots → underscores**: Always use `.replace(".", "_")` for Firebase keys
2. **Nested vs flat constructs**: Use `flatten_construct()` before comparisons
3. **N/A handling**: PACA outputs "N/A" → auto-scores 0 (see `is_none_or_na()`)
4. **Memory leakage**: Without `@st.cache_resource`, agents lose conversation history on rerun
5. **Expert name sanitization**: `sanitize_firebase_key()` required for Firebase keys (different from `sanitize_key()`)
6. **Aggregation**: "Symptom 1-N" → "Symptom name" happens in `get_aggregated_scoring_options()`, not per-element

## Key Files Reference

- `SP_utils.py`: Core agent creation, Firebase I/O, sanitization
- `evaluator.py`: PSYCHE RUBRIC, construct normalization, scoring
- `expert_validation_utils.py`: Validation-specific scoring, aggregation logic
- `firebase_config.py`: Firebase initialization
- `paca_construct_generator.py`, `sp_construct_generator.py`: Post-conversation construct generation
- `EVALUATOR_REFACTOR.md`, `MEMORY_FIX_GUIDE.md`, `VALIDATION_CODE_REVIEW.md`: Architecture decision records

## Language

- **UI**: Korean (환자, 전문가, 검증 등)
- **Code**: English comments + Korean strings
- **Data**: Mixed (prompts in Korean, keys in English)
