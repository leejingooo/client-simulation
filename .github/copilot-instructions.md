# Client Simulation - Copilot Instructions

## Project Overview

This is a **psychiatric evaluation research platform** that simulates patient-clinician interactions using two AI agents:

- **SP (Simulated Patient)**: LLM-based agent that mimics psychiatric patients based on profiles and behavioral instructions
- **PACA (Psychiatric Assessment Conversational Agent)**: LLM-based clinician agent that conducts psychiatric interviews

The system generates conversations, produces structured psychiatric assessments ("constructs"), evaluates PACA performance against ground truth (SP constructs), and enables expert validation by psychiatrists.

**Tech Stack**: Streamlit + LangChain + Firebase Realtime Database + OpenAI/Anthropic APIs

## Core Architecture

### Three-Layer Agent System

1. **SP Agent** (`SP_utils.py`, `sp_construct_generator.py`)
   - Built with LangChain + ChatOpenAI/ChatAnthropic (gpt-5.1 default model)
   - Configured via: profile JSON, history narrative, behavioral instructions loaded from Firebase
   - Uses `InMemoryChatMessageHistory` for conversation state
   - **Critical**: Cached with `@st.cache_resource` to persist across Streamlit reruns - without this, memory resets!
   - Created via `create_conversational_agent()` which returns `(agent, memory)` tuple

2. **PACA Agent** (`PACA_*_utils.py`, `paca_construct_generator.py`)
   - Multiple variants: `claude_basic`, `claude_guided`, `gpt_basic`, `gpt_guided`, `llama`
   - **Model configuration by variant**:
     - `gpt_basic`: `gpt-5-nano` (temperature=0.7, streaming)
     - `gpt_guided`: `gpt-5.1` (temperature=0.7, streaming)
     - `claude_basic/guided`: `claude-3-5-sonnet-20240620` (temperature=0.7)
   - Each has initial greeting prompt hardcoded (e.g., "안녕하세요, 저는 정신과 의사...")
   - Generates psychiatric constructs by querying itself post-conversation
   - **Critical**: Must be cached in `st.session_state.paca_agent` and `st.session_state.paca_memory`
   - Created via `create_paca_agent(version, page_id)` which returns `(agent, memory, version)` tuple
   - **Memory isolation**: `page_id` parameter ensures separate memory for each experiment page when multiple pages are open simultaneously

3. **Evaluator** (`evaluator.py`, `expert_validation_utils.py`)
   - Compares PACA construct vs SP construct (ground truth)
   - Uses **PSYCHE RUBRIC** - standardized psychiatric evaluation criteria (59 elements across 3 categories)
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
- **Maximum PSYCHE Score: 55** - Sum of all weights (each element scored 0-1, then multiplied by weight)
  - Weight 1 elements: 10개 (max contribution: 10)
  - Weight 5 elements: 5개 (max contribution: 25)
  - Weight 2 elements: 10개 (max contribution: 20)
  - **Total: 10 + 25 + 20 = 55**
  - All scoring functions (G-Eval, Binary, Impulsivity, Behavior) return normalized scores 0-1
  - Final weighted score = Σ(element_score × weight)
- Multiple "Symptom 1-N" entries → aggregated to single "Symptom name" for expert validation
- PACA constructs are **flat** (`{"Mood": "depressed"}`), SP constructs are **nested** (`{"Mental Status Examination": {"Mood": "depressed"}}`)
- `flatten_construct()` in `evaluator.py` normalizes both to flat structure

### Evaluation vs Expert Validation

**Two separate workflows**:

1. **Automated Evaluation** (`pages/연구자용 격리 폴더 (연구모드시 페이지 복원)/04_evaluation.py`):
   - **Purpose**: Automated PACA performance assessment using PSYCHE RUBRIC
   - **Process**: Compares PACA construct vs SP construct (ground truth) programmatically
   - **Output**: PSYCHE Score (0-55 range) + detailed element-level scores
   - **Firebase storage**: `clients_{client_num}/psyche_{diagnosis}_{model}_{exp_num}`
     - Key format: `psyche_mdd_gptbasic_1111` (lowercase, no underscores in model name)
   - **Scoring methods**: G-Eval (LLM-based, 0-1), binary (0 or 1), impulsivity/behavior (0, 0.5, or 1)
   - **Usage**: Research-only page (in 연구자용 격리 폴더) for generating performance metrics

2. **Expert Validation** (`pages/06_expert_validation.py`):
   - **Purpose**: Human expert review of PACA outputs for quality assessment
   - **Process**: Psychiatrists manually rate PACA construct accuracy
   - **Output**: Expert-validated scores (different scale/purpose than PSYCHE)
   - **Firebase storage**: `expert_{sanitized_name}_{client_num}_{exp_num}`
   - **Scoring**: Experts choose "Correct", "Partially Correct", "Incorrect" for each element
   - **Usage**: Validation study with domain experts

**Critical distinction**: PSYCHE scores are NOT generated by expert validation - they come from the automated evaluation page!

## Development Workflows

### Running the Application

**Dev Container Setup** (`.devcontainer/devcontainer.json`):
- **Base image**: `mcr.microsoft.com/devcontainers/python:1-3.11-bullseye`
- **Auto-installs** on container creation via `updateContentCommand`:
  - System packages from `packages.txt` (apt install)
  - Python packages from `requirements.txt` + streamlit (pip3 install --user)
- **Auto-runs** on attach via `postAttachCommand`:
  - `streamlit run Home.py --server.enableCORS false --server.enableXsrfProtection false`
- **Port 8501**: Auto-forwarded with preview on auto-forward
- **Extensions**: `ms-python.python`, `ms-python.vscode-pylance`

**Manual start** (if needed):
```bash
streamlit run Home.py --server.enableCORS false --server.enableXsrfProtection false
```

**Critical**: Port 8501 must be accessible for Streamlit UI. Dev container auto-handles this.

**Local Development** (outside dev container):
```bash
# Install dependencies
pip3 install -r requirements.txt

# Set environment variables (create .env file)
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"

# Run Streamlit
streamlit run Home.py --server.enableCORS false --server.enableXsrfProtection false
```

### Running Experiments

**Critical Setup Pattern** - Each experiment page (`pages/01_experiment(BD|MDD|OCD)_<model>_<type>.py`):

1. **Import base experiment logic**: `from Experiment_<model>_<type> import experiment_page` (e.g., `Experiment_gpt_basic`, `Experiment_claude_guided`)
2. **Set client number** - **Disorder mapping** (research cohort):
   - `client_number = 6201` → Major Depressive Disorder (MDD)
   - `client_number = 6202` → Bipolar Disorder (BD)
   - `client_number = 6206` → Obsessive-Compulsive Disorder (OCD)
   - **Legacy numbers**: 6101-6107 (older patient profiles, still in use on some pages)
3. **Session state reset** on page change to prevent memory leakage:
   ```python
   if st.session_state.current_page != current_page:
       # Clear all agent/memory state
       if 'paca_agent' in st.session_state:
           del st.session_state.paca_agent
       st.session_state.force_paca_update = True
   ```

**Version presets** at top of base Experiment files (`Experiment_claude_basic.py`):
```python
profile_version = 6.0      # SP profile structure version
beh_dir_version = 6.0      # Behavioral directive version
con_agent_version = 6.0    # System prompt version
paca_version = 3.0         # PACA agent version
```

**Agent creation pattern** (must preserve memory!):
```python
# SP Agent
sp_agent, sp_memory = create_conversational_agent(
    f"{profile_version:.1f}".replace(".", "_"),  # "6_0"
    f"{beh_dir_version:.1f}".replace(".", "_"),
    client_number,
    con_agent_system_prompt
)
# MUST store memory in session state
if 'sp_memory' not in st.session_state:
    st.session_state.sp_memory = sp_memory

# PACA Agent - check for forced update
# CRITICAL: page_id ensures memory isolation when multiple experiment pages are open
page_id = f"{model_type}_client{client_number}"  # e.g., "gpt_basic_client6201"
if 'paca_agent' not in st.session_state or st.session_state.get('force_paca_update', False):
    st.session_state.paca_agent, st.session_state.paca_memory, version = create_paca_agent(paca_version, page_id=page_id)
    st.session_state.force_paca_update = False

# Initial greeting setup - CRITICAL for memory consistency
# Add BEFORE creating conversation_generator to avoid duplicates
initial_greeting = "안녕하세요, 저는 정신과 의사 김민수입니다. 이름이 어떻게 되시나요?"
if len(paca_memory.messages) == 0 or paca_memory.messages[-1].content != initial_greeting:
    paca_memory.add_ai_message(initial_greeting)
if len(sp_memory.messages) == 0 or sp_memory.messages[-1].content != initial_greeting:
    sp_memory.add_user_message(initial_greeting)
```

**Conversation flow** (uses generator pattern):
```python
# Start simulation - yields ("PACA", msg) or ("SP", msg) tuples
# Store generator in session state to preserve across reruns
# NOTE: Initial greeting must be added to memories BEFORE creating generator
if 'conversation_generator' not in st.session_state:
    st.session_state.conversation_generator = simulate_conversation(
        st.session_state.paca_agent, 
        sp_agent,
        max_turns=300  # Default limit
    )

for speaker, message in st.session_state.conversation_generator:
    st.write(f"**{speaker}**: {message}")
    st.session_state.conversation.append((speaker, message))
```

**Construct generation** (post-conversation):
```python
# PACA construct - queries agent about what it learned
paca_construct = create_paca_construct(paca_agent)

# SP construct - ground truth from profile
sp_construct = create_sp_construct(client_number, profile_version)
```

**Experiment number validation** (prevents overwrites):
```python
if check_experiment_number_exists(firebase_ref, client_number, exp_number):
    st.error("Experiment number already used")
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

**Conversation generator pattern** - Critical for preserving conversation state:
```python
# Generator must be stored in session_state to survive reruns
if 'conversation_generator' not in st.session_state:
    st.session_state.conversation_generator = simulate_conversation(
        st.session_state.paca_agent,
        sp_agent,
        max_turns=300
    )

# Iterate WITHOUT reassigning - generator maintains state internally
for speaker, message in st.session_state.conversation_generator:
    # Process messages...
```

**Critical**: Do NOT recreate the generator on each rerun - it will reset the conversation!

**Why generators for conversations**:
- Streamlit reruns on every interaction - normal functions would restart the conversation
- Generators yield one turn at a time and maintain their internal state
- Stored in `st.session_state`, they survive reruns and continue from where they left off
- Conversation flow: PACA speaks → SP responds → PACA speaks → ... (alternating via `yield`)

### Streamlit Page Structure

- `Home.py`: Authentication (checks `st.secrets["participant"]`), Playwright setup
- `pages/01_experiment(BD|MDD|OCD)_<model>_<type>.py`: Experiment runners per disorder/model
  - Each page imports base logic: `from Experiment_<model>_<type> import experiment_page`
  - Pages set `client_number` and tracking vars, then call `experiment_page(client_number)`
  - **Page cleanup pattern**: On page change, delete all agent/memory session state + set `force_paca_update=True`

- `pages/00_진행상태_확인.py`: Experiment progress monitoring dashboard
- `pages/01_에이전트에_대한_전문가_검증.py`: Expert validation interface for PACA agents
- `pages/02_가상환자에_대한_전문가_검증.py`: SP authenticity validation by experts
- `pages/05_json2csv.py`: Utility for converting Firebase JSON exports to CSV
- `pages/08_sp_validation_viewer.py`: View SP validation results
- `pages/09_plot.py`: PSYCHE score visualization (matplotlib scatter plot)
  - **Data source**: Loads from `clients_{client_num}/psyche_{diagnosis}_{model}_{exp_num}`
  - **NOT from expert validation data** - uses automated evaluation results
  - **Score range**: 0-55 (max possible PSYCHE score)
- `pages/연구자용 격리 폴더 (연구모드시 페이지 복원)/`: Research-mode pages
  - **Critical**: These pages are hidden in normal mode but contain essential evaluation logic
  - **Must review**: When updating copilot instructions, ALWAYS review pages in this folder
  - `04_evaluation.py`: Automated PACA evaluation (generates PSYCHE scores)
  - Contains all disorder-specific experiment pages (MDD, BD, OCD)
  - Contains unified experiment pages allowing client selection via dropdown

**Navigation pattern**:
```python
st.session_state.validation_stage = 'intro'  # State machine for multi-page flows
st.rerun()  # Trigger page refresh
```

### Expert Validation Workflow

`pages/01_에이전트에_대한_전문가_검증.py` - **Multi-stage wizard** for psychiatric expert review:

1. **PRESET Configuration** (top of file):
   ```python
   EXPERIMENT_NUMBERS = [
       (6201, 11),   # (client_number, experiment_number)
       (6201, 12),   # MDD patient, experiment 12
       (6202, 211),  # BD patient, experiment 211
       (6206, 611),  # OCD patient, experiment 611
       # Total 24 experiments across 3 disorders × 2 models × 2 variants × 2 reps
   ]
   ```

2. **Three-stage flow** (controlled by `st.session_state.validation_stage`):
   - `intro`: Instructions page
   - `test`: Practice validation with sample data
   - `validation`: Loop through all EXPERIMENT_NUMBERS

3. **Scoring pattern** - Uses aggregated options:
   ```python
   # Get all scoring options grouped by PSYCHE category
   scoring_options = get_aggregated_scoring_options(construct_data)
   # Returns: {category: [{element, options, paca_value}, ...]}
   
   # Expert selects from dropdown options
   for category, elements in scoring_options.items():
       for item in elements:
           expert_choice = st.selectbox(
               item['element'],
               options=item['options']
           )
   
   # Auto-calculate score based on expert choices
   validation_result = create_validation_result(
       construct_data, 
       expert_responses,  # Dict of {element: choice}
       (client_num, exp_num)
   )
   ```

4. **Result structure** (changed from `expert_score` to `psyche_score`):
   ```json
   {
     "elements": {
       "Symptom name": {  // Aggregated from Symptom 1-N
         "expert_choice": "Correct",
         "paca_content": "- insomnia\n- anxiety\n- depressed mood",
         "score": 1,
         "weight": 1,
         "weighted_score": 1
       }
     },
     "psyche_score": 35.5,  // Total weighted score
     "metadata": {...}
   }
   ```

5. **Firebase save** (auto-sanitizes expert name):
   ```python
   save_validation_to_firebase(
       firebase_ref, expert_name, (client_num, exp_num), result
   )
   # Saves to: expert_<sanitized_name>_<client>_<exp>
   # e.g., expert_kim_soo_min_6101_101
   ```

## Common Patterns & Conventions

### Creating New Experiment Pages

To add a new experiment page (e.g., for a new PACA variant or client):

1. **Copy an existing page**: `pages/01_experiment(<disorder>)_<model>_<type>.py`
2. **Update imports**: Change `from Experiment_X import` to match your base experiment file
3. **Set client number**: Use appropriate number from disorder mapping
4. **Update page tracking**: Change `current_page` and `current_agent_type` strings
5. **Key pattern**: Pages import base logic, only override `client_number` and tracking vars

Example structure:
```python
from Experiment_gpt_basic import experiment_page
client_number = 6201  # MDD
current_page = "mdd)_gpt_basic.py"
current_agent_type = "GPT Basic"

if st.session_state.current_page != current_page:
    # Clear state and force agent recreation
    if 'paca_agent' in st.session_state:
        del st.session_state.paca_agent
    st.session_state.force_paca_update = True

if __name__ == "__main__":
    experiment_page(client_number)
```

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

**Streamlit Secrets** (`st.secrets` or `.streamlit/secrets.toml`):
- `firebase`: Service account JSON for Firebase Admin SDK (must include: `type`, `project_id`, `private_key_id`, `private_key`, `client_email`)
- `firebase_database_url`: Realtime Database URL (e.g., `https://project-id.firebaseio.com`)
- `participant`: List of allowed expert names for authentication (checked in `Home.py`)

**Environment/API Keys** (loaded automatically):
- `OPENAI_API_KEY`: For GPT models (default SP model: `gpt-5.1`)
- `ANTHROPIC_API_KEY`: For Claude models (PACA variants)

**Firebase Initialization** (`firebase_config.py`):
```python
# Success message indicates proper setup
firebase_ref = get_firebase_ref()
# Shows: "시스템 준비가 완료되었습니다."
```

## Testing & Debugging

**Testing Pattern** (no standard test framework):
- Test files are standalone Python scripts (not pytest/unittest)
- Run directly: `python test_expert_validation_aggregation.py`
- Tests validate data transformations and Firebase structure matching
- Key test files:
  - `test_expert_validation_aggregation.py`: Symptom aggregation logic
  - `test_comprehensive_field_mapping.py`: PSYCHE RUBRIC field mapping
  - `test_firebase_sanitized_structure.py`: Firebase key sanitization
  - `test_marriage_key_consistency.py`: Slash vs underscore handling

**Common Debugging Commands**:
```bash
# Check Python environment (dev container auto-configures)
python --version  # Should be 3.11

# Test Firebase connection
python -c "from firebase_config import get_firebase_ref; get_firebase_ref()"

# Run test suite
python test_comprehensive_field_mapping.py

# Manual Streamlit start (if auto-start fails)
streamlit run Home.py --server.enableCORS false --server.enableXsrfProtection false
```

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

**Debug agent state** (common Streamlit issue):
```python
# Check if agent is properly cached
if 'paca_agent' in st.session_state:
    st.write("PACA agent exists in session")
    st.write(f"Memory: {len(st.session_state.paca_memory.messages)} messages")
```

## Known Gotchas

1. **Version dots → underscores**: Always use `.replace(".", "_")` for Firebase keys
2. **Nested vs flat constructs**: Use `flatten_construct()` before comparisons
3. **N/A handling**: PACA outputs "N/A" → auto-scores 0 (see `is_none_or_na()`)
4. **Memory leakage**: Without `@st.cache_resource`, agents lose conversation history on rerun
5. **Expert name sanitization**: `sanitize_firebase_key()` required for Firebase keys (different from `sanitize_key()`)
6. **Aggregation**: "Symptom 1-N" → "Symptom name" happens in `get_aggregated_scoring_options()`, not per-element
7. **Session state on page change**: Must explicitly delete and recreate `paca_agent`/`paca_memory` when switching between experiment pages - set `force_paca_update=True`
8. **Model configuration**: SP uses `gpt-5.1` by default (see `SP_utils.py`), PACA variants use different models per implementation
9. **Authentication flow**: `Home.py` checks `st.secrets["participant"]` list - all pages call `check_participant()` or equivalent before rendering
10. **Field name normalization**: `get_value_from_construct()` normalizes spaces to underscores (e.g., "Triggering factor" matches "triggering_factor") - see CODE_REVIEW_REPORT.txt
11. **Marriage/Relationship History key**: In-memory constructs use `"Marriage/Relationship History"` (slash), but Firebase sanitizes to `"Marriage_Relationship History"` (underscore) via `sanitize_dict()` - code must handle both
12. **Firebase sanitization**: `sanitize_dict()` converts `/$#[].` to `_` before saving - all slashes become underscores in stored data
13. **Initial greeting memory timing**: The hardcoded initial greeting "안녕하세요, 저는 정신과 의사 김민수입니다..." must be added to PACA and SP memories BEFORE creating `conversation_generator` - check for duplicates using `if len(memory.messages) == 0 or memory.messages[-1].content != greeting`

## Key Files Reference

- `SP_utils.py`: Core agent creation, Firebase I/O, sanitization
- `evaluator.py`: PSYCHE RUBRIC, construct normalization, scoring, **field name normalization (space↔underscore)**
- `expert_validation_utils.py`: Validation-specific scoring, aggregation logic
- `firebase_config.py`: Firebase initialization
- `paca_construct_generator.py`, `sp_construct_generator.py`: Post-conversation construct generation
- `Experiment_claude_basic.py` (and variants): Base experiment logic imported by page-specific files
- `EVALUATOR_REFACTOR.md`, `MEMORY_FIX_GUIDE.md`, `VALIDATION_CODE_REVIEW.md`: Architecture decision records
- `CODE_REVIEW_REPORT.txt`: Comprehensive review of field mapping issues (Dec 2025)

## Testing

**Test aggregation logic**:
```bash
python test_expert_validation_aggregation.py
```
This verifies that symptom aggregation and scoring options match expected format.

**Test field mapping** (critical for PSYCHE RUBRIC):
```bash
python test_comprehensive_field_mapping.py
```
Validates all 59 PSYCHE elements map correctly between SP/PACA constructs.

**Test Firebase structure**:
```bash
python test_firebase_sanitized_structure.py
```
Ensures key sanitization matches actual Firebase data structure.

**Test Marriage/Relationship key handling** (critical for slash vs underscore):
```bash
python test_marriage_key_consistency.py
```

**Check Firebase connection**:
```python
from firebase_config import get_firebase_ref
ref = get_firebase_ref()
# Should show "시스템 준비가 완료되었습니다."
```

## Language

- **UI**: Korean (환자, 전문가, 검증 등)
- **Code**: English comments + Korean strings
- **Data**: Mixed (prompts in Korean, keys in English)
