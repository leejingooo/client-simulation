# Client Simulation - Copilot Instructions

**Last Updated**: January 2026 (includes recall failure mechanism for MDD patients)

## First Time Setup

**If this is your first time working with this codebase:**

1. **Open in dev container** - VSCode will prompt to "Reopen in Container" (required for Python 3.11 environment)
2. **Wait for auto-install** - Container runs `updateContentCommand` to install system packages (chromium) and Python dependencies
3. **Wait for auto-start** - Container runs `postAttachCommand` to start Streamlit on port 8501
4. **Configure secrets** - Create `.streamlit/secrets.toml` with:
   ```toml
   [firebase]
   type = "service_account"
   project_id = "your-project-id"
   private_key_id = "..."
   private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
   client_email = "..."
   
   firebase_database_url = "https://your-project.firebaseio.com"
   
   [participant]
   names = ["expert1", "expert2", ...]
   ```
5. **Set API keys** - Add to `.streamlit/secrets.toml` or environment:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
6. **Verify startup** - Look for "You can now view your Streamlit app in your browser" message
7. **Access UI** - Click forwarded port 8501 or navigate to `http://localhost:8501`

**Ready state**: When you see the Streamlit UI with authentication prompt, you're ready to go!

## Quick Start

**For immediate productivity:**
1. **Dev container auto-starts everything** - Wait for "You can now view your Streamlit app in your browser" message
2. **Firebase secrets required** - Ensure `st.secrets["firebase"]`, `st.secrets["firebase_database_url"]`, and `st.secrets["participant"]` are configured
3. **Main entry point**: [Home.py](Home.py) - Streamlit runs on port 8501
4. **Key directories**: `pages/` (experiment pages), `data/prompts/` (agent instructions), see [Project Structure](#project-structure)
5. **Common workflows**: [Running Experiments](#running-experiments), [Creating New Pages](#creating-new-experiment-pages)
6. **Memory critical**: Always store agents in `st.session_state` (see [Memory Management](#memory-management-critical))
7. **System prompt testing**: Use [pages/21_System_Prompt_Test.py](pages/21_System_Prompt_Test.py) to iteratively test prompts before production

## Project Overview

This codebase implements the **PSYCHE (Patient Simulation for Yielding psyCHiatric assessment conversational agent Evaluation) framework**, a research platform for evaluating psychiatric assessment conversational agents (PACAs) through construct-grounded simulation and evaluation.

**Research Context**: Peer-reviewed research paper currently in **revision stage**. Re-running experiments with updated configurations. Focus on methodology, not historical results.

### Core Concepts

- **PACA (Psychiatric Assessment Conversational Agent)**: AI agent that conducts psychiatric interviews - the **subject of evaluation**
- **PSYCHE-SP (Simulated Patient)**: LLM-based patient agent fed with Multi-faceted Construct (MFC) - serves as **ground truth** for PACA evaluation
- **MFC (Multi-faceted Construct)**: Clinically grounded psychiatric schema with 3 components:
  1. **MFC-Profile**: Patient demographics, symptoms, history (analogous to medical records)
  2. **MFC-History**: Dynamic life story and biographical narrative
  3. **MFC-Behavior**: Observable behavioral instructions based on Mental Status Examination (MSE)
- **Construct-SP**: Selected MFC elements serving as evaluation reference (ground truth)
- **Construct-PACA**: PACA's predictions of patient's psychiatric state after interview
- **PSYCHE SCORE**: Quantitative evaluation metric (0-55 range) comparing Construct-PACA vs Construct-SP

**Two Key Principles**:
1. **Construct-grounded patient utterance simulation**: PSYCHE-SP generates realistic patient responses based on MFC
2. **Construct-grounded evaluation**: PACA performance measured by accuracy in discerning MFC elements

**Target Disorders** (7 total): Major Depressive Disorder (MDD), Bipolar Disorder (BD), Panic Disorder (PD), Generalized Anxiety Disorder (GAD), Social Anxiety Disorder (SAD), Obsessive-Compulsive Disorder (OCD), Post-Traumatic Stress Disorder (PTSD)

**Tech Stack**: Streamlit + LangChain + Firebase Realtime Database + OpenAI/Anthropic APIs

## Project Structure

```
/workspaces/client-simulation/
├── Home.py                          # Entry point, authentication, Playwright setup
├── SP_utils.py                      # SP agent creation, Firebase I/O, key sanitization
├── PACA_*_utils.py                  # PACA agent variants (gpt_basic, claude_guided, etc.)
├── evaluator.py                     # PSYCHE RUBRIC definitions, automated scoring
├── expert_validation_utils.py       # Expert validation scoring, aggregation logic
├── firebase_config.py               # Firebase initialization
├── Experiment_*.py                  # Base experiment logic (imported by pages)
├── sp_construct_generator.py        # SP construct generation post-conversation
├── paca_construct_generator.py      # PACA construct generation post-conversation
├── pages/                           # Streamlit pages (auto-discovered by framework)
│   ├── 10_재실험.py                # Re-experiment page for client 6301 (2 repetitions)
│   ├── 12_PSYCHE-Expert_Correlation.py  # Expert vs PSYCHE score comparison (6 validators × 24 experiments)
│   ├── 13_SP_Quantitative.py       # SP quantitative validation data extraction (4.1 validation metrics)
│   ├── 14_SP_Qualitative.py        # SP qualitative validation data extraction (4.2 Likert scale analysis)
│   ├── 15_Figure_Generator.py      # Publication-quality figure generation (Helvetica font, paper figures)
│   ├── 16_MFC_Viewer.py            # MFC data viewer (Profile, History, Behavior inspection tool)
│   ├── 17_Conversation_log_viewer.py  # SP-Expert conversation log viewer (validation studies)
│   ├── 18_MDD_MFC_Editor.py        # MFC editor for client 6301 (MDD patient - new patient cohort)
│   ├── 21_System_Prompt_Test.py    # Interactive system prompt editor and SP testing interface
│   ├── SP_validation/              # SP validation page subfolder
│   ├── deprecated/                 # Deprecated pages (archived)
│   ├── 연구자용 격리 폴더 (연구모드시 페이지 복원)/  # Research-mode pages (hidden in production)
│   ├── 연구자용 격리 폴더 2 (연구모드시 페이지 복원)/  # Additional research pages
│   └── 연구자용 격리 폴더 3 (실험시 있었던 파일들)/  # Archived experiment files
│       ├── 01_experiment(MDD|BD|OCD)_<model>_<type>.py  # Experiment pages per disorder/model
│       ├── 01_unified_<model>_<type>.py  # Unified experiment pages with client selection
│       ├── 04_evaluation.py        # Automated PACA evaluation tool (4.4)
│       ├── 19_MFC_Copier.py        # MFC data cloning utility (e.g., 6201→6301)
│       ├── 20_Upload_System_Prompt_to_Firebase.py  # One-time utility to upload system prompts to Firebase
│       └── 02_generation, 02_viewer, 03_ai_ai_viewer (접근제한).py  # Other research tools
├── data/
│   ├── prompts/                    # Agent system prompts (versioned)
│   │   ├── con-agent_system_prompt/  # SP system prompts (SP-Prompt-1/2/3)
│   │   └── paca_system_prompt/       # PACA prompts (basic vs guided)
│   ├── input/                      # Patient profiles, behavioral directives
│   └── output/                     # Generated conversation logs
├── .devcontainer/
│   └── devcontainer.json           # Dev container config (Python 3.11, auto-start)
├── .github/
│   └── copilot-instructions.md     # This file
├── packages.txt                    # System packages (chromium for Playwright)
├── requirements.txt                # Python dependencies
└── test_*.py                       # Test scripts (no pytest/unittest framework)
```

## Core Architecture

### PSYCHE Framework Components

#### 1. MFC Generation System

**Sequential generation pipeline** (in `data/prompts/`):
1. **MFC-Profile generation**: Based on user input (diagnosis/age/sex)
   - Contains 9 categories: Identifying data, Chief complaint, Present illness, Past psychiatric history, Past medical history, Family history, Developmental and social history, Marriage/relationship history, Impulsivity
   - Analogous to psychiatric medical records - multi-faceted patient schema
   - Some elements have fixed values per disorder (e.g., impulsivity elements)
2. **MFC-History generation**: Conditioned on MFC-Profile
   - Dynamic lifetime biography complementing short-answer Profile
   - Not used in PSYCHE SCORE calculation (enrichment only)
3. **MFC-Behavior generation**: Conditioned on Profile + History
   - Based on Mental Status Examination (MSE) - "snapshot" of current mental state
   - Observable behavioral aspects: mood, affect, thought process, verbal productivity, etc.
   - Critical for behavioral alignment with real patients

**Rationale**: Sequential chain prevents "lost-in-the-middle" problem with long contexts, ensures clinically consistent patient behavior

#### 2. PSYCHE-SP Agent (`SP_utils.py`, `sp_construct_generator.py`)
   - Built with LangChain + ChatOpenAI/ChatAnthropic (gpt-4o-2024-11-20 in paper, gpt-5.1-2025-11-13 currently)
   - **Fed with entire MFC** (Profile + History + Behavior) as psychiatric schema
   - Uses `InMemoryChatMessageHistory` for conversation state
   - **Critical**: Cached with `@st.cache_resource` to persist across Streamlit reruns - without this, memory resets!
   - Created via `create_conversational_agent()` which returns `(agent, memory)` tuple
   - **Three system prompt components** (SP-Prompt-1/2/3):
     1. MFC explanation
     2. Methods for generating utterances grounded in MFC elements
     3. Instructions aligning LLM with real psychiatric patients (counters assistant-tuning bias)
   - **Recall Failure Mechanism** (added 2026-01-03 for MDD patients):
     - **Purpose**: Simulates memory/recall difficulties common in depression
     - **Activation**: MDD patients have probability (default 0.8, configurable) to enter "recall failure mode" for 2 turns when asked about past details (onset, duration, triggers, stressors, alleviating/exacerbating factors)
     - **Detection**: Regex/keyword detector (`is_past_detail_question()`) identifies past-detail questions
     - **State machine**: If topic changes (non-past-detail question), mode immediately deactivates
     - **Behavior**: Patient responds vaguely ("not sure") initially, may recall partially if clinician re-asks with specificity
     - **Implementation**: Mode injected via `{recall_failure_mode}` placeholder in system prompt (must be present)
     - **Configuration**: `RECALL_FAILURE_PROB = 0.8` (line 410 in SP_utils.py), `RECALL_FAILURE_TURNS = 2`
   - **System Prompt Storage**: System prompts now stored in Firebase at `system_prompts/con-agent_version6_0`
     - Local files still exist in `data/prompts/con-agent_system_prompt/` for backup
     - Use page 21_System_Prompt_Test to edit and test prompts interactively
     - Use page 20_Upload_System_Prompt_to_Firebase to upload local prompts to Firebase
   - **Research purpose**: Ground truth for PACA evaluation - simulates realistic patient behavior

#### 3. PACA Agent (`PACA_*_utils.py`, `paca_construct_generator.py`)
   - **Subject of evaluation** - interviews PSYCHE-SP to assess psychiatric state
   - Multiple variants: `claude_basic`, `claude_guided`, `gpt_basic`, `gpt_guided`, `llama`
   - **Model configuration by variant** (paper uses gpt-4o and claude-3-5-sonnet):
     - `gpt_basic` / `gptsmaller`: `gpt-4o-mini-2024-07-18` (temperature=0.7, streaming)
     - `gpt_guided` / `gptlarge`: `gpt-5.1-2025-11-13` (temperature=0.7, streaming)
     - `claude_basic` / `claudesmaller`: `claude-3-haiku-20240307` (temperature=0.7)
     - `claude2` / `claudelarge`: `claude-3-5-sonnet-20240620` (temperature=0.7)
   - **Prompt types**: Basic vs Guided (guided expected to perform better per paper validation)
   - Each has initial greeting prompt hardcoded (e.g., "안녕하세요, 저는 정신과 의사 김민수입니다...")
   - **Construct-PACA generation**: After interview, PACA answers element-by-element questions about patient's MFC (e.g., "What is the patient's Mood?")
   - **Critical**: Must be cached in `st.session_state.paca_agent` and `st.session_state.paca_memory`
   - Created via `create_paca_agent(version, page_id)` which returns `(agent, memory, version)` tuple
   - **Memory isolation**: `page_id` parameter ensures separate memory for each experiment page when multiple pages are open simultaneously
   - **Research purpose**: Demonstrates clinical assessment competence through accurate MFC discernment

#### 4. Evaluation System (`evaluator.py`, `expert_validation_utils.py`)
   - Compares **Construct-PACA** (PACA's predictions) vs **Construct-SP** (ground truth from MFC)
   - Uses **PSYCHE RUBRIC** - standardized psychiatric evaluation criteria
   - **59 elements across 3 weight categories**:
     - **Subjective (w=1)**: 10 elements - patient-reported information (chief complaint, symptoms, triggers, stressors, family history)
     - **Impulsivity (w=5)**: 5 elements - safety-critical risk assessment (suicidal ideation/plan/attempt, self-harm risk, homicide risk)
     - **Behavior (w=2)**: 10 elements - MSE-based observations (mood, affect, thought process/content, insight, verbal productivity)
   - **Maximum PSYCHE Score: 55** (sum of all weighted scores)
   - **Four scoring methods**:
     1. **G-Eval**: LLM-based semantic similarity for open-ended elements (chief complaint, symptom names, triggers, affect, perception, thought process/content)
     2. **Binary**: Exact match (0 or 1) for simple categorical elements
     3. **Impulsivity**: Delta-based ordinal scoring with safety bias (underestimation = 0 score)
     4. **Behavior**: Ordinal value mapping with distance penalty (|Δ| > 1 = 0 score)
   - **Clinical rationale**: Weights reflect ethical importance (safety), task complexity (MSE observation), and information type (subjective reporting)
   - **Research purpose**: Enables quantitative, automated, and clinically meaningful PACA performance measurement

### Data Storage: Firebase Realtime Database

**All data lives in Firebase** with sanitized keys (no `$#[].`):

```python
# Key patterns (see SP_utils.sanitize_key):
clients/<client_number>/profile_version6_0  # Underscores replace dots
clients/<client_number>/beh_dir_version6_0
clients_<client_num>_psyche_<disorder>_<model>_<exp_num>  # PSYCHE scores (ROOT level)
```

**Critical Firebase Data Loading Patterns**:
1. **Version numbers**: `6.0` → `version6_0` in Firebase paths
2. **PSYCHE scores location**: Stored at **ROOT level** with key `clients_{client_num}_psyche_{disorder}_{model}_{exp_num}`
   - NOT nested under `clients/{client_num}/` path
   - Example: `clients_6201_psyche_mdd_gptsmaller_3111`
3. **Expert validation scores**: Stored at ROOT level as `expert_{sanitized_name}_{client_num}_{exp_num}`
4. **Loading pattern for analysis pages**: 
   ```python
   # Get ALL root-level keys first
   all_data = firebase_ref.get()
   for key in all_data.keys():
       if "_psyche_" in key and key.startswith("clients_"):
           # Parse and process
   ```
5. **Model name in keys**: No underscores - use `gptsmaller`, `gptlarge`, `claudesmaller`, `claudelarge` (not `gpt_smaller`)

**See**: `09_plot.py` lines 90-140 for working Firebase data loading example
```

**Critical**: Version numbers like `6.0` → `version6_0` in Firebase paths (see `save_to_firebase`/`load_from_firebase` in `SP_utils.py`)

## PSYCHE RUBRIC - Central Evaluation Schema

Defined in `evaluator.py` and `expert_validation_utils.py`:

```python
PSYCHE_RUBRIC = {
    # Subjective (weight=1): G-Eval scoring
    "Chief complaint": {"type": "g-eval", "weight": 1},
    "Symptom name": {"type": "g-eval", "weight": 1},
    
    # Impulsivity (weight=5): Delta-based with safety bias
    "Suicidal ideation": {"type": "impulsivity", "weight": 5, 
                          "values": {"high": 2, "moderate": 1, "low": 0}},
    
    # Behavior (weight=2): Ordinal scales with distance penalty
    "Mood": {"type": "behavior", "weight": 2, 
             "values": {"depressed": 1, "dysphoric": 2, "euthymic": 3, 
                       "elated": 4, "euphoric": 5, "irritable": 5}},
}
```

**Key patterns**:
- **Maximum PSYCHE Score: 55** - Sum of all weights (59 total elements)
  - Weight 1 elements: 10개 (Subjective) = max 10 points
  - Weight 5 elements: 5개 (Impulsivity) = max 25 points  
  - Weight 2 elements: 10개 (MSE-Behavior) = max 20 points
  - **Total: 10 + 25 + 20 = 55**
- **Scoring methods with clinical rationale**:
  - **G-Eval** (LLM semantic similarity, 0-1): For open-ended narrative responses
    - Examples: Chief complaint, Symptom names, Triggering factors, Stressors, Affect, Thought process/content
    - Uses gpt-4o-2024-11-20 with custom prompts
  - **Binary** (0 or 1): For categorical yes/no elements
    - Examples: Symptom length, Suicidal plan, Suicidal attempt history, Spontaneity
  - **Impulsivity** (safety-biased, 0/0.5/1): Δ = (PACA value) - (SP value)
    - If Δ < 0 (underestimation): Score = 0 (critical safety failure)
    - If Δ = 0 (correct): Score = 1
    - If Δ = 1: Score = 0.5, If Δ = 2: Score = 0
    - Applies to: Suicidal ideation, Self-mutilating behavior risk, Homicide risk
  - **Behavior** (distance-penalized, 0/0.5/1): |Δ| > 1 = 0 score
    - Rationale: States differing by >1 point are clinically distinct
    - Mood: depressed(1)↔dysphoric(2)↔euthymic(3)↔elated(4)↔euphoric/irritable(5)
    - Verbal productivity: decreased(0)↔moderate(1)↔increased(2)
    - Insight: true emotional(1)↔intellectual(2)↔external blame(3)↔slight awareness(4)↔complete denial(5)
- **Symptom aggregation**: Multiple "Symptom 1-N" entries → single "Symptom name" for expert validation
- **Construct structure**: PACA (flat) vs SP (nested) → both flattened via `flatten_construct()`
- **Paper validation**: Correlation remains high (min Pearson's r = 0.7802) across varied weights, proving rubric robustness

### Research Validation Studies (Paper Sections 4.1-4.4)

#### 4.1 SP Quantitative Validation (`pages/02_가상환자에_대한_전문가_검증.py`)
- **Purpose**: Validate PSYCHE-SP authenticity - do simulated patients behave like real psychiatric patients?
- **Method**: 10 psychiatrists evaluate 14 PSYCHE-SP cases (7 disorders × 2 repetitions)
- **Evaluation**: 24-element Construct-SP review (Appropriate/Inappropriate per element)
- **Metrics**: 
  - Conformity score (%) = proportion of psychiatrists rating element as "appropriate"
  - Inter-observer reliability: Gwet's AC1 = 0.87, simple agreement = 0.89
  - Intra-observer reliability: PABAK = 0.86, simple agreement = 0.94 (repeat MDD case)
- **Paper results**: Average conformity 93% (range 85-97%), proving clinical appropriateness
- **SP_SEQUENCE preset** (lines 18-33): 14 cases with randomized order
  - Client numbers: 6201-6207 representing 7 distinct disorders
  - Each disorder appears twice with different behavioral variations

#### 4.2 SP Qualitative Validation (`pages/02_가상환자에_대한_전문가_검증.py`)
- **Purpose**: Collect expert impressions on SP believability and clinical realism
- **Method**: After each SP quantitative validation, experts provide open-ended feedback
- **Evaluation**: Free-text fields for diagnostic accuracy, behavioral authenticity, improvement areas
- **Paper findings**: Board-certified psychiatrist (K.L.) validated clinical appropriateness across all 7 disorders
  - MDD: Decreased energy, psychomotor retardation, reluctance to use term "depressed"
  - BD: Euphoric mood, labile affect, flight of ideas, limited insight
  - Anxiety: Anxious affect, somatic symptoms, increased suicide risk
  - OCD: Intrusive thoughts, compulsive behaviors, ego-dystonic symptoms
  - PTSD: Trauma-related nightmares, avoidance behaviors, emotional reactivity
- **Integration**: Same page as 4.1, separate stage after construct validation

#### 4.3 PACA Quantitative Validation (`pages/01_가상면담가에_대한_전문가_검증.py`)
- **Purpose**: Validate PACA clinical assessment competence - does it accurately assess patients?
- **Method**: Expert psychiatrists evaluate 24 experiments (3 disorders × 4 model variants × 2 reps)
- **Evaluation**: Element-by-element Construct-PACA vs Construct-SP comparison using PSYCHE RUBRIC
- **Scoring**: Correct (1.0), Partially Correct (0.5), Incorrect (0.0) per element → weighted PSYCHE Score (0-55)
- **Paper results**: 
  - Strong correlation with expert scores: Pearson's r = 0.8486, p < 0.0001, n=20
  - Moderate correlation with PIQSCA (interview quality scale): Pearson's r = 0.6367, p = 0.0025
  - Guided prompt PACAs consistently outperformed basic prompt PACAs
- **EXPERIMENT_NUMBERS preset** (lines 60-87): 24 experiments
  - Client numbers: 6201 (MDD), 6202 (BD), 6206 (OCD)
  - Model variants: gptsmaller, gptlarge, claudesmaller, claudelarge
  - Experiment numbering: `<disorder_digit><model_digit><variant_digit><rep_digit>`

#### 4.4 Automated PACA Evaluation (`pages/연구자용 격리 폴더/04_evaluation.py`)
- **Purpose**: Algorithmic PACA evaluation without human experts - enables scalability
- **Method**: Automated construct comparison using G-Eval, binary, and ordinal scoring
- **Workflow**:
  1. Search available experiments in Firebase (filter by client/experiment number range)
  2. Select experiment from dropdown
  3. Load Construct-SP (ground truth) and Construct-PACA
  4. Run PSYCHE RUBRIC evaluation element-by-element
  5. Save results to Firebase as `clients_{client_num}/psyche_{diagnosis}_{model}_{exp_num}`
- **Validation**: Page 11 correlation analysis compares automated vs expert scores
- **Firebase key format**: `psyche_mdd_gptbasic_1111` (lowercase, no underscores in model name)
- **Usage**: Research page hidden in production - for rapid iteration and pre-screening

#### Paper Ablation Study
- **Compared** 3 SP variants: PSYCHE-SP (full MFC), NoMFCBehavior (Profile+History only), NoMFC (simple "act-like-patient" prompt)
- **Results**: PSYCHE-SP significantly outperformed others (ANOVA p<0.05)
  - Speech/thought process: PSYCHE-SP > NoMFC (p=0.047)
  - Affect: PSYCHE-SP > both NoMFCBehavior and NoMFC (p<0.001)
  - Mood: Trend toward PSYCHE-SP superiority (p=0.078)
- **Conclusion**: MFC-Behavior is critical - MSE-based behavioral instructions essential for realism

## Development Workflows

### Running the Application

**Dev Container Setup** (`.devcontainer/devcontainer.json`):
- **Base image**: `mcr.microsoft.com/devcontainers/python:1-3.11-bullseye`
- **Python version**: 3.11 required (enforced by dev container, critical for dependencies)
- **Auto-installs** on container creation via `updateContentCommand`:
  - System packages from `packages.txt` (apt install - includes chromium)
  - Python packages from `requirements.txt` + streamlit (pip3 install --user)
  - Prints: `✅ Packages installed and Requirements met`
- **Auto-runs** on attach via `postAttachCommand`:
  - `streamlit run Home.py --server.enableCORS false --server.enableXsrfProtection false`
- **Port 8501**: Auto-forwarded with preview on auto-forward
- **Extensions**: `ms-python.python`, `ms-python.vscode-pylance`
- **Auto-opens**: `README.md` and `Home.py` on container start
- **Ready state**: Container is fully operational when Streamlit shows `You can now view your Streamlit app in your browser.`
- **Virtual environment**: A `.venv` directory exists but dev container uses system Python (packages installed with `--user` flag)

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
   - **Primary cohort (6201-6207)**: Used in paper validation studies
     - `client_number = 6201` → Major Depressive Disorder (MDD)
     - `client_number = 6202` → Bipolar Disorder (BD)
     - `client_number = 6203` → Panic Disorder (PD)
     - `client_number = 6204` → Generalized Anxiety Disorder (GAD)
     - `client_number = 6205` → Social Anxiety Disorder (SAD)
     - `client_number = 6206` → Obsessive-Compulsive Disorder (OCD)
     - `client_number = 6207` → Post-Traumatic Stress Disorder (PTSD)
   - **New cohort (6301+)**: New patient profiles for extended research
     - `client_number = 6301` → MDD (editable via page 18_MDD_MFC_Editor.py)
   - **Legacy cohort (6101-6107)**: Older patient profiles (still in use on some pages)
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
- `pages/01_가상면담가에_대한_전문가_검증.py`: Expert validation interface for PACA agents (Section 4.3)
- `pages/02_가상환자에_대한_전문가_검증.py`: SP authenticity validation by experts (Sections 4.1, 4.2)
- `pages/05_json2csv.py`: Utility for converting Firebase JSON exports to CSV
- `pages/08_sp_validation_viewer.py`: View SP validation results
- `pages/09_plot.py`: PSYCHE score visualization (matplotlib scatter plot)
  - **Data source**: Loads from `clients_{client_num}/psyche_{diagnosis}_{model}_{exp_num}`
  - **NOT from expert validation data** - uses automated evaluation results
  - **Score range**: 0-55 (max possible PSYCHE score)
- `pages/10_plot2.py`: Alternative visualization with 5 experiments per model variant
  - Supports larger datasets with filled/hatched markers for model differentiation
  - Uses same Firebase data structure as `09_plot.py`
- `pages/10_plot3.py`: Scatter plot optimized for smaller vs large model comparison
  - Uses diamond/circle markers with filled/empty/hatched styles
  - Aligned with current EXPERIMENT_NUMBERS preset (24 experiments)
- `pages/11_correlation_analysis.py`: Statistical correlation analysis page
  - **Purpose**: Compare expert validation scores vs automated PSYCHE scores to measure agreement
  - **Methods**: 
    - Pearson correlation (linear relationship, normal distribution)
    - Spearman correlation (monotonic relationship, non-parametric)
  - **Visualizations**: 
    - Overall scatter plots with regression lines showing expert vs automated scores
    - Category-level breakdowns (Subjective, Impulsivity, Behavior)
    - Correlation heatmaps showing relationships across PSYCHE elements
  - **Data sources**: 
    - Expert validation data from `expert_{name}_{client}_{exp}` paths
    - Automated evaluation results from `clients_{client_num}_psyche_{diagnosis}_{model}_{exp_num}` (ROOT level)
  - **PRESET configuration**: Uses same `EXPERIMENT_NUMBERS` list as expert validation (24 experiments across 3 disorders × 4 model variants × 2 reps)
  - **Key functions**: `calculate_correlation()`, `create_correlation_heatmap()`, element-level analysis
- `pages/12_PSYCHE-Expert_Correlation.py`: Expert score aggregation and comparison page
  - **Purpose**: Aggregate 6 expert validators' scores and compare with automated PSYCHE scores
  - **Validators**: 이강토, 김태환, 김광현, 김주오, 허율, 장재용
  - **Data loading**:
    - Expert scores: `expert_{sanitized_name}_{client_num}_{exp_num}` (ROOT level)
    - PSYCHE scores: `clients_{client_num}_psyche_{disorder}_{model}_{exp_num}` (ROOT level)
    - Calculates average across all 6 validators per experiment
  - **Visualizations**: Overall correlation plot + disorder-specific plots (MDD, BD, OCD)
  - **Critical**: Must load ALL Firebase root keys first (`firebase_ref.get()`), then filter by pattern
  - **Experiment number → model mapping**: Uses explicit `MODEL_BY_EXP` dictionary
    - **Pattern**: Define `MODEL_BY_EXP = {exp_num: 'model_name', ...}` for all 24 experiments
    - **Lookup function**: `get_model_from_exp(exp_num)` returns model name or 'unknown'
    - **Example mapping**:
      - MDD (6201): 3111, 3117 → gptsmaller | 1121, 1123 → gptlarge | 3134, 3138 → claudesmaller | 1143, 1145 → claudelarge
      - BD (6202): 3211, 3212 → gptsmaller | 1221, 1222 → gptlarge | 3231, 3234 → claudesmaller | 1241, 1242 → claudelarge
      - OCD (6206): 3611, 3612 → gptsmaller | 1621, 1622 → gptlarge | 3631, 3632 → claudesmaller | 1641, 1642 → claudelarge
    - **Why explicit dict**: Avoids fragile substring parsing, supports all disorder numbering schemes
- `pages/15_Figure_Generator.py`: Publication-quality figure generation for research paper
  - **Purpose**: Generate publication-ready figures with consistent styling (Helvetica font, IEEE/academic standards)
  - **Features**: 
    - Automated figure generation from Firebase data
    - Consistent styling: Helvetica font family, seaborn "ticks" style
    - Multiple figure types: scatter plots, box plots, correlation matrices, bar charts
    - Export options: PNG, PDF, SVG (high-resolution, 300 DPI minimum)
  - **EXPERIMENT_NUMBERS preset**: Same 24 experiments as expert validation (3 disorders × 4 models × 2 reps)
  - **Usage**: Select figure type → configure parameters → generate → download
  - **Critical**: All matplotlib/seaborn plots use `rcParams['font.family'] = 'Helvetica'` for consistency
- `pages/15_Figure_Generator_Lite.py`: Lightweight version of figure generator with simplified interface
- `pages/16_MFC_Viewer.py`: MFC (Multi-faceted Construct) inspection and verification tool
  - **Purpose**: View and verify MFC components (Profile, History, Behavior) stored in Firebase
  - **Client-Disorder mapping**:
    - 6201: MDD, 6202: BD, 6203: PD, 6204: GAD, 6205: SAD, 6206: OCD, 6207: PTSD
    - 6301: MDD (new patient cohort, editable via page 18)
  - **Features**:
    - Load and display all three MFC components side-by-side
    - Version selection (default: 6.0 → `version6_0` in Firebase)
    - JSON export for manual inspection or backup
    - Structured display with expandable sections per MFC category
  - **Data loading**: `load_mfc_data(firebase_ref, client_number, version="6_0")`
    - Returns: `{'profile': {...}, 'history': str, 'behavior': str}`
  - **Usage**: Select client number → choose version → view/export MFC data
  - **Critical for**: Debugging MFC generation, verifying prompt outputs, validating construct consistency
- `pages/17_Conversation_log_viewer.py`: SP-Expert conversation log viewer for validation studies
  - **Purpose**: View and analyze conversation logs between Expert validators and SP from validation studies (Sections 4.1-4.2)
  - **Data source**: `sp_conversation_{validator_name}_{client_num}_{page_num}` keys in Firebase
  - **Features**:
    - Filter by validator, client number, or disorder
    - Display conversation with alternating Expert/SP messages
    - Export conversations as TXT files
    - Statistics dashboard (conversations by validator/disorder)
  - **Message structure**: 
    - Even indices (0, 2, 4...) = Expert messages
    - Odd indices (1, 3, 5...) = SP responses
  - **Usage**: Select filters → choose conversation → review dialogue → export if needed
  - **Related pages**: Page 13 (SP Quantitative), Page 14 (SP Qualitative), Page 16 (MFC Viewer)
- `pages/18_MDD_MFC_Editor.py`: Interactive MFC editor for client 6301 (new MDD patient cohort)
  - **Purpose**: Edit and update MFC components (Profile, History, Behavioral Directive) for new patient profiles
  - **Target client**: 6301 (MDD patient - extensible pattern for other 6301+ clients)
  - **Features**:
    - Side-by-side comparison (current vs. edited content)
    - JSON validation with error handling
    - Three-tab interface for Profile/History/Behavior editing
    - Confirmation workflow to prevent accidental overwrites
    - Real-time Firebase save with version control (version 6_0)
  - **Workflow**: 
    1. Load current MFC data from Firebase
    2. Edit JSON content in right-side text areas (left side shows current)
    3. Validate JSON format before saving
    4. Confirm changes with warning message
    5. Save to Firebase with automatic backup
  - **Critical**: Depends on 19_MFC_Copier (in 연구자용 격리 폴더 3) to initially clone 6201→6301 data
  - **Use case**: Creating new patient variations without affecting validated research cohort (6201-6207)
  - **Related pages**: Page 16 (MFC Viewer for read-only inspection), Page 19 (MFC Copier for cloning)
- `pages/19_Case_Analysis_6201_1145.py`: Detailed case analysis for specific experiment (client 6201, exp 1145)
  - **Purpose**: Deep-dive analysis of individual experiment results for publication case studies
  - **Features**: Conversation analysis, construct comparison, scoring breakdown
- `pages/21_System_Prompt_Test.py`: Interactive system prompt editor and SP testing interface
  - **Purpose**: Real-time system prompt editing and immediate SP behavioral testing without affecting production
  - **Two modes**: 
    1. **Edit mode**: Side-by-side system prompt editor with validation
    2. **Chat mode**: Interactive conversation with SP using test prompt
  - **Features**:
    - **Dual-panel editor**: Current prompt (read-only) vs. edited prompt (editable)
    - **Required placeholder validation**: Ensures `{given_information}`, `{current_date}`, `{profile_json}`, `{history}`, `{behavioral_instruction}`, `{recall_failure_mode}` are present
    - **Recall Failure probability slider**: Configure activation probability (0.0-1.0) for MDD patients
    - **Test-first workflow**: Save to temporary Firebase path (`con-agent_version6_0_test`) before production
    - **Real-time chat interface**: Test SP behavior immediately after editing prompt
    - **Conversation persistence**: Save test conversations to Firebase for analysis
  - **Workflow**:
    1. Load current prompt from Firebase `system_prompts/con-agent_version6_0`
    2. Edit prompt in right panel (validates placeholders)
    3. Click "테스트만 하기" to enter chat mode with test prompt
    4. Conduct test conversation with SP (client 6301 by default)
    5. If satisfied, click "Firebase에 저장" to update production prompt
  - **Critical**: Production experiments (10_재실험 etc.) still use local files - Firebase storage is for future migration
  - **Use case**: Iterative prompt engineering, debugging SP behavior, testing recall failure mechanism
  - **Related pages**: Page 20 (Upload local prompts to Firebase), Page 18 (Edit MFC for test client 6301)
- `pages/10_재실험.py`: Re-experiment page for client 6301 (MDD patient, new cohort)
  - **Purpose**: Run repeated experiments with new patient profile (6301) to validate updated configurations
  - **Configuration**: 2 repetitions of client 6301 (MDD) as defined in `SP_SEQUENCE`
  - **Workflow**: Same as validation pages - SP Construct generation followed by expert scoring interface
  - **Target client**: 6301 (new MDD patient created via page 18 MFC Editor)
  - **Note**: Part of paper revision - testing new patient cohort and updated system prompts
- `pages/22_MDD재실험_검증_결과_뷰어.py`: Validation results viewer for 6301 client experiments
  - **Purpose**: View and analyze validation results from 6 expert validators for client 6301 re-experiments
  - **Validators**: 이강토, 김태환, 김광현, 김주오, 허율, 장재용
  - **Features**:
    - Display all validation results grouped by validator
    - Show SP validation data (construct reviews)
    - View conversation logs between validators and SP
    - Track validation progress per validator
  - **Data sources**: `sp_validation_*_6301_*`, `sp_conversation_*_6301_*`, `validation_progress_*` keys
  - **Use case**: Monitor and analyze expert validation completion for 6301 re-experiment study
  - **Related pages**: Page 10 (10_재실험), Page 02 (SP validation interface)
- `pages/연구자용 격리 폴더 (연구모드시 페이지 복원)/`: Research-mode pages
  - Contains disorder-specific experiment pages: `01_experiment(MDD|BD|OCD)_<model>_<type>.py`
  - Contains unified experiment pages with client selection: `01_unified_<model>_<type>.py`
  - Contains `04_evaluation.py`: Automated PACA evaluation tool (generates PSYCHE scores by comparing SP vs PACA constructs)
  - Contains access-restricted tools: `02_generation.py`, `02_viewer.py`, `03_ai_ai_viewer.py`
  - Historical experiment pages: `01_환자_*.py`
- `pages/연구자용 격리 폴더 3 (실험시 있었던 파일들)/`: Archived experiment files
  - Contains `19_MFC_Copier.py`: Utility for cloning MFC data between client numbers (e.g., 6201→6301)
  - Used for creating new patient cohorts without manual recreation of MFC components
  - Workflow: Select source client → select target client → copy Profile/History/Behavior → validate in MFC Viewer
  - Contains `20_Upload_System_Prompt_to_Firebase.py`: One-time utility to upload local system prompts to Firebase
  - Workflow: Read local `con-agent_system_prompt_version6.0.txt` → upload to `system_prompts/con-agent_version6_0` in Firebase

**Navigation pattern**:
```python
st.session_state.validation_stage = 'intro'  # State machine for multi-page flows
st.rerun()  # Trigger page refresh
```

### Expert Validation Workflow

`pages/01_가상면담가에_대한_전문가_검증.py` - **Multi-stage wizard** for psychiatric expert review:

1. **PRESET Configuration** (top of file):
   ```python
   # Current configuration: Smaller vs Large model comparison
   EXPERIMENT_NUMBERS = [
       # 6201 MDD
       (6201, 3111), (6201, 3117),  # gptsmaller
       (6201, 1121), (6201, 1123),  # gptlarge
       (6201, 3134), (6201, 3138),  # claudesmaller
       (6201, 1143), (6201, 1145),  # claudelarge
       # Similar patterns for 6202 BD and 6206 OCD
       # Total 24 experiments across 3 disorders × 4 model variants × 2 reps
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

4. **Result structure**:
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
     "psyche_score": 35.5,  // Total weighted score (0-55 range)
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
- All tests print clear pass/fail messages with detailed output
- Key test files:
  - `test_expert_validation_aggregation.py`: Symptom aggregation logic
  - `test_comprehensive_field_mapping.py`: PSYCHE RUBRIC field mapping (59 elements)
  - `test_firebase_sanitized_structure.py`: Firebase key sanitization
  - `test_marriage_key_consistency.py`: Slash vs underscore handling
  - `test_evaluator_issue.py`: Specific evaluator edge cases

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
8. **Model configuration**: 
   - SP: `gpt-5.1` (default, see `SP_utils.py`)
   - PACA variants: `gpt-4o-mini` (basic/smaller), `gpt-5.1` (guided/large), `claude-3-haiku` (basic/smaller), `claude-3-5-sonnet` (claude2/large)
   - **Model naming evolution**: Original terminology was `gptbasic`/`gptguided`, now uses `gptsmaller`/`gptlarge` to reflect model size comparison
9. **Authentication flow**: `Home.py` checks `st.secrets["participant"]` list - all pages call `check_participant()` or equivalent before rendering
10. **Field name normalization**: `get_value_from_construct()` normalizes spaces to underscores (e.g., "Triggering factor" matches "triggering_factor") - **FIXED Dec 2025**, see [CODE_REVIEW_REPORT.txt](CODE_REVIEW_REPORT.txt)
11. **Marriage/Relationship History key**: In-memory constructs use `"Marriage/Relationship History"` (slash), expert validation fixed to use slash format - **FIXED Dec 2025**, see [CODE_REVIEW_REPORT.txt](CODE_REVIEW_REPORT.txt)
12. **Firebase sanitization**: `sanitize_dict()` converts `/$#[].` to `_` before saving - all slashes become underscores in stored data
13. **Initial greeting memory timing**: The hardcoded initial greeting "안녕하세요, 저는 정신과 의사 김민수입니다..." must be added to PACA and SP memories BEFORE creating `conversation_generator` - check for duplicates using `if len(memory.messages) == 0 or memory.messages[-1].content != greeting`
14. **Playwright setup**: Chromium browser required for certain features - auto-installed on dev container startup via `setup_playwright()` in [Home.py](Home.py)
15. **Recall failure placeholder**: System prompts MUST contain `{recall_failure_mode}` placeholder - automatically appended if missing in SP agent creation
16. **Firebase system prompts**: Production prompts at `system_prompts/con-agent_version6_0`, test prompts at `system_prompts/con-agent_version6_0_test`
17. **Recall failure configuration**: Default probability is 0.8 (80%) in production (`SP_utils.py` line 410), but configurable in page 21 test interface (0.0-1.0)
18. **Firebase data loading for analysis pages**: 
    - Always load ALL root keys first: `all_data = firebase_ref.get()`
    - NEVER use `firebase_ref.child(key).get()` in a loop without checking root first
    - PSYCHE scores are at ROOT level, not nested under `clients/`
    - Key pattern matching: `if "_psyche_" in key and key.startswith("clients_")`
    - See [pages/09_plot.py](pages/09_plot.py) lines 90-140 for correct pattern
19. **Experiment number → model mapping**:
    - Use explicit `MODEL_BY_EXP` dictionary (not substring parsing) - see pages/12 and 15
    - Pattern: `MODEL_BY_EXP = {3111: 'gptsmaller', 1121: 'gptlarge', ...}` for all 24 experiments
    - Lookup: `get_model_from_exp(exp_num)` returns model name or 'unknown'
    - Different disorders use different numbering schemes (MDD=31xx/11xx, BD=32xx/12xx, OCD=36xx/16xx)

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

## Dependencies & Requirements

**Core Dependencies** (`requirements.txt`):
- `streamlit`: Main web framework
- `langchain`, `langchain_anthropic`, `langchain_openai`, `langchain-ollama`: LLM orchestration
- `openai`, `anthropic`: AI model APIs
- `firebase-admin`: Firebase Realtime Database integration
- `pandas`, `matplotlib`, `seaborn`: Data processing and visualization
- `scipy`, `pingouin`: Statistical analysis (correlation, reliability)
- `playwright`: Browser automation (Chromium installed via `packages.txt`)
- `python-dotenv`: Environment variable management
- `requests`, `pydantic`: HTTP and data validation

**System Packages** (`packages.txt`):
- `chromium`: Required for Playwright browser automation

**Python Version**: 3.11 (enforced by dev container - do NOT use other versions)

**Critical Setup Requirements**:
1. Firebase service account JSON in `st.secrets["firebase"]`
2. Firebase Realtime Database URL in `st.secrets["firebase_database_url"]`
3. Participant list in `st.secrets["participant"]` for authentication
4. `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` environment variables

## Quick Reference: Common Tasks

**Add a new experiment page**:
1. Copy existing page: `pages/01_experiment(disorder)_model_type.py`
2. Update import to match base experiment file
3. Set client number (6201=MDD, 6202=BD, 6206=OCD)
4. Update `current_page` and `current_agent_type` tracking strings

**Add a new visualization page**:
1. Define `EXPERIMENTS` dict with disorder→model→experiment list mapping
2. Use consistent model names: `gptsmaller_guided`, `gptlarge_guided`, `claudesmaller_guided`, `claudelarge_guided`
3. Set up color mapping for disorders (MDD=red, BD=teal, OCD=orange)
4. Configure marker styles for model differentiation (see `10_plot2.py`, `10_plot3.py` for patterns)

**Debug memory issues**:
```python
# Check agent caching
st.write(f"Agent in session: {'paca_agent' in st.session_state}")
st.write(f"Memory messages: {len(st.session_state.paca_memory.messages)}")

# Verify generator state
st.write(f"Generator exists: {'conversation_generator' in st.session_state}")
```

**Add new PSYCHE RUBRIC element**:
1. Add to `PSYCHE_RUBRIC` dict in `evaluator.py` with type, weight, values
2. Update `get_aggregated_scoring_options()` in `expert_validation_utils.py` if needed
3. Run `python test_comprehensive_field_mapping.py` to verify mapping

**Change agent models**:
- SP: Edit model name in `SP_utils.py` (default: `gpt-5.1`)
- PACA: Edit model in specific `PACA_*_utils.py` file (e.g., `PACA_gpt_basic_utils.py`)

**Firebase data structure**:
- All data under `clients/<client_num>/` or `expert_<name>_<client>_<exp>`
- Keys auto-sanitized: dots→underscores, slashes→underscores
- Test with: `python test_firebase_sanitized_structure.py`

**Debug Firebase data loading** (for analysis pages):
```python
# Check what keys exist
firebase_ref = get_firebase_ref()
all_data = firebase_ref.get()
if all_data:
    # Look for PSYCHE scores
    psyche_keys = [k for k in all_data.keys() if "_psyche_" in k]
    print(f"Found {len(psyche_keys)} PSYCHE score keys")
    
    # Look for expert scores
    expert_keys = [k for k in all_data.keys() if k.startswith("expert_")]
    print(f"Found {len(expert_keys)} expert validation keys")
    
    # Inspect a sample key
    if psyche_keys:
        sample = psyche_keys[0]
        print(f"Sample: {sample}")
        data = all_data[sample]
        print(f"Has psyche_score: {'psyche_score' in data}")
```

**Troubleshoot experiment number parsing**:
```python
# Test get_model_from_exp() function
test_exp_nums = [3111, 1121, 3134, 1143, 3211, 1221]
for exp_num in test_exp_nums:
    model = get_model_from_exp(exp_num)
    print(f"{exp_num} → {model}")
# Should output: gptsmaller, gptlarge, claudesmaller, claudelarge, etc.
```
**Inspect MFC data for a client**:
```python
# Using MFC Viewer page (16_MFC_Viewer.py) or directly:
from firebase_config import get_firebase_ref
from SP_utils import sanitize_key

firebase_ref = get_firebase_ref()
client_num = 6201  # MDD patient
version = "6_0"

# Load all three components
profile = firebase_ref.child(f"clients/{client_num}/profile_version{version}").get()
history = firebase_ref.child(f"clients/{client_num}/history_version{version}").get()
behavior = firebase_ref.child(f"clients/{client_num}/beh_dir_version{version}").get()

# Or use the MFC Viewer page UI for browsing
```