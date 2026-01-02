"""
Conversation Log Viewer
SP-Expert 대화 내역 확인 페이지

Displays conversation logs between SP (Simulated Patient) and Expert validators
from SP validation studies (sections 4.1-4.2)
"""

import streamlit as st
import pandas as pd
from firebase_config import get_firebase_ref
from expert_validation_utils import sanitize_firebase_key

# ================================
# Configuration
# ================================
st.set_page_config(
    page_title="Conversation Log Viewer",
    page_icon="💬",
    layout="wide"
)

# ================================
# Client to Disorder Mapping
# ================================
CLIENT_DISORDER_MAP = {
    6201: 'MDD',  # Major Depressive Disorder
    6202: 'BD',   # Bipolar Disorder
    6203: 'PD',   # Panic Disorder
    6204: 'GAD',  # Generalized Anxiety Disorder
    6205: 'SAD',  # Social Anxiety Disorder
    6206: 'OCD',  # Obsessive-Compulsive Disorder
    6207: 'PTSD'  # Post-Traumatic Stress Disorder
}

# ================================
# Data Loading Functions
# ================================
def get_all_conversation_keys(firebase_ref):
    """Get all sp_conversation keys from Firebase.
    
    Returns:
        list: List of conversation keys matching pattern sp_conversation_*
    """
    all_data = firebase_ref.get()
    if not all_data:
        return []
    
    conversation_keys = [
        key for key in all_data.keys() 
        if key.startswith("sp_conversation_")
    ]
    return sorted(conversation_keys)


def parse_conversation_key(key):
    """Parse conversation key to extract validator name, client number, and page number.
    
    Args:
        key: Conversation key (e.g., "sp_conversation_김주오_6201_1")
    
    Returns:
        dict: {'validator': str, 'client_num': int, 'page_num': int, 'disorder': str}
              or None if parsing fails
    """
    try:
        # Remove prefix
        parts = key.replace("sp_conversation_", "").split("_")
        
        if len(parts) < 3:
            return None
        
        # Last part is page number
        page_num = int(parts[-1])
        # Second to last is client number
        client_num = int(parts[-2])
        # Everything else is validator name
        validator = "_".join(parts[:-2])
        
        disorder = CLIENT_DISORDER_MAP.get(client_num, "Unknown")
        
        return {
            'validator': validator,
            'client_num': client_num,
            'page_num': page_num,
            'disorder': disorder
        }
    except (ValueError, IndexError):
        return None


def load_conversation(firebase_ref, key):
    """Load conversation data from Firebase.
    
    Args:
        firebase_ref: Firebase reference
        key: Conversation key
    
    Returns:
        list: List of message dicts [{'role': 'Expert/SP', 'content': str}, ...]
    """
    data = firebase_ref.child(key).get()
    
    if not data or 'conversation' not in data:
        return []
    
    conversation = data['conversation']
    messages = []
    
    # Handle both list and dict formats
    if isinstance(conversation, list):
        # Conversation is a list
        for idx, msg in enumerate(conversation):
            if msg and isinstance(msg, dict) and 'content' in msg:
                # Determine role based on position (even=Expert, odd=SP)
                role = "Expert" if idx % 2 == 0 else "SP"
                messages.append({
                    'index': idx,
                    'role': role,
                    'content': msg['content']
                })
    elif isinstance(conversation, dict):
        # Conversation is a dict with numeric string keys
        sorted_indices = sorted([int(k) for k in conversation.keys()])
        
        for idx in sorted_indices:
            msg = conversation[str(idx)]
            if 'content' in msg:
                # Determine role based on position (even=Expert, odd=SP)
                role = "Expert" if idx % 2 == 0 else "SP"
                messages.append({
                    'index': idx,
                    'role': role,
                    'content': msg['content']
                })
    
    return messages


def filter_conversations(conversation_keys, validator_filter=None, client_filter=None, disorder_filter=None):
    """Filter conversation keys based on criteria.
    
    Args:
        conversation_keys: List of all conversation keys
        validator_filter: Validator name to filter (None = all)
        client_filter: Client number to filter (None = all)
        disorder_filter: Disorder to filter (None = all)
    
    Returns:
        list: Filtered conversation keys
    """
    filtered = []
    
    for key in conversation_keys:
        parsed = parse_conversation_key(key)
        if not parsed:
            continue
        
        # Apply filters
        if validator_filter and parsed['validator'] != validator_filter:
            continue
        if client_filter and parsed['client_num'] != client_filter:
            continue
        if disorder_filter and parsed['disorder'] != disorder_filter:
            continue
        
        filtered.append(key)
    
    return filtered


def get_unique_validators(conversation_keys):
    """Extract unique validator names from conversation keys."""
    validators = set()
    for key in conversation_keys:
        parsed = parse_conversation_key(key)
        if parsed:
            validators.add(parsed['validator'])
    return sorted(list(validators))


def get_unique_clients(conversation_keys):
    """Extract unique client numbers from conversation keys."""
    clients = set()
    for key in conversation_keys:
        parsed = parse_conversation_key(key)
        if parsed:
            clients.add(parsed['client_num'])
    return sorted(list(clients))


# ================================
# Main UI
# ================================
st.title("💬 Conversation Log Viewer")
st.markdown("SP-Expert 대화 내역 확인 (SP Validation Studies - Sections 4.1-4.2)")

# Initialize Firebase
firebase_ref = get_firebase_ref()

# Load all conversation keys
with st.spinner("Loading conversation list from Firebase..."):
    all_keys = get_all_conversation_keys(firebase_ref)

if not all_keys:
    st.error("❌ No conversation logs found in Firebase")
    st.info("Expected key format: `sp_conversation_{validator_name}_{client_num}_{page_num}`")
    st.stop()

st.success(f"✅ Found {len(all_keys)} conversation logs")

# ================================
# Filters
# ================================
st.markdown("---")
st.subheader("🔍 Filters")

col1, col2, col3 = st.columns(3)

# Get unique values for filters
unique_validators = get_unique_validators(all_keys)
unique_clients = get_unique_clients(all_keys)
unique_disorders = sorted(list(set(CLIENT_DISORDER_MAP.values())))

with col1:
    validator_options = ["All"] + unique_validators
    validator_filter = st.selectbox(
        "검증자 (Validator)",
        validator_options,
        index=0
    )
    validator_filter = None if validator_filter == "All" else validator_filter

with col2:
    client_options = ["All"] + [str(c) for c in unique_clients]
    client_filter = st.selectbox(
        "환자번호 (Client Number)",
        client_options,
        index=0
    )
    client_filter = None if client_filter == "All" else int(client_filter)

with col3:
    disorder_options = ["All"] + unique_disorders
    disorder_filter = st.selectbox(
        "진단 (Disorder)",
        disorder_options,
        index=0
    )
    disorder_filter = None if disorder_filter == "All" else disorder_filter

# Apply filters
filtered_keys = filter_conversations(
    all_keys,
    validator_filter=validator_filter,
    client_filter=client_filter,
    disorder_filter=disorder_filter
)

st.info(f"📊 Filtered: {len(filtered_keys)} conversations")

# ================================
# Conversation List
# ================================
st.markdown("---")
st.subheader("📋 Conversation List")

if not filtered_keys:
    st.warning("No conversations match the selected filters")
    st.stop()

# Create table with conversation metadata
conversation_table = []
for key in filtered_keys:
    parsed = parse_conversation_key(key)
    if parsed:
        conversation_table.append({
            'Key': key,
            'Validator': parsed['validator'],
            'Client': parsed['client_num'],
            'Disorder': parsed['disorder'],
            'Page': parsed['page_num']
        })

df = pd.DataFrame(conversation_table)

# Display as interactive table
st.dataframe(
    df,
    use_container_width=True,
    hide_index=True
)

# ================================
# Conversation Viewer
# ================================
st.markdown("---")
st.subheader("💬 View Conversation")

# Select conversation to view
conversation_options = [
    f"{parsed['validator']} | Client {parsed['client_num']} ({parsed['disorder']}) | Page {parsed['page_num']}"
    for key in filtered_keys
    if (parsed := parse_conversation_key(key))
]

if conversation_options:
    selected_idx = st.selectbox(
        "Select conversation to view:",
        range(len(conversation_options)),
        format_func=lambda i: conversation_options[i]
    )
    
    selected_key = filtered_keys[selected_idx]
    
    # Load conversation
    with st.spinner("Loading conversation..."):
        messages = load_conversation(firebase_ref, selected_key)
    
    if not messages:
        st.error("❌ Failed to load conversation data")
        st.stop()
    
    # Display conversation metadata
    parsed = parse_conversation_key(selected_key)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Validator", parsed['validator'])
    with col2:
        st.metric("Client", f"{parsed['client_num']} ({parsed['disorder']})")
    with col3:
        st.metric("Page", parsed['page_num'])
    with col4:
        st.metric("Messages", len(messages))
    
    st.markdown("---")
    
    # Display conversation
    st.markdown("### 대화 내역")
    
    for msg in messages:
        role = msg['role']
        content = msg['content']
        
        # Use different styling for Expert vs SP
        if role == "Expert":
            st.markdown(f"**🩺 Expert ({parsed['validator']}):**")
            st.info(content)
        else:  # SP
            st.markdown(f"**🧑‍⚕️ SP (Client {parsed['client_num']}):**")
            st.success(content)
        
        st.markdown("")  # Add spacing
    
    # Export option
    st.markdown("---")
    st.subheader("💾 Export")
    
    # Create text export
    export_text = f"Conversation: {parsed['validator']} | Client {parsed['client_num']} ({parsed['disorder']}) | Page {parsed['page_num']}\n"
    export_text += "=" * 80 + "\n\n"
    
    for msg in messages:
        role = msg['role']
        content = msg['content']
        export_text += f"[{role}]: {content}\n\n"
    
    st.download_button(
        label="📥 Download as TXT",
        data=export_text,
        file_name=f"{selected_key}.txt",
        mime="text/plain"
    )

# ================================
# Statistics
# ================================
st.markdown("---")
st.subheader("📊 Statistics")

# Count by validator
validator_counts = {}
for key in filtered_keys:
    parsed = parse_conversation_key(key)
    if parsed:
        validator = parsed['validator']
        validator_counts[validator] = validator_counts.get(validator, 0) + 1

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Conversations by Validator:**")
    for validator, count in sorted(validator_counts.items(), key=lambda x: x[1], reverse=True):
        st.write(f"- {validator}: {count}")

with col2:
    # Count by disorder
    disorder_counts = {}
    for key in filtered_keys:
        parsed = parse_conversation_key(key)
        if parsed:
            disorder = parsed['disorder']
            disorder_counts[disorder] = disorder_counts.get(disorder, 0) + 1
    
    st.markdown("**Conversations by Disorder:**")
    for disorder, count in sorted(disorder_counts.items(), key=lambda x: x[1], reverse=True):
        st.write(f"- {disorder}: {count}")

# ================================
# Help Section
# ================================
st.markdown("---")
with st.expander("ℹ️ Help & Information"):
    st.markdown("""
    ### Conversation Log Viewer
    
    This page displays conversation logs between Expert validators and SP (Simulated Patients) 
    from the SP validation studies (Paper Sections 4.1-4.2).
    
    **Data Structure:**
    - Firebase key format: `sp_conversation_{validator_name}_{client_num}_{page_num}`
    - Conversations are stored as numbered message pairs
    - Even indices (0, 2, 4...) are Expert messages
    - Odd indices (1, 3, 5...) are SP responses
    
    **Filters:**
    - **Validator**: Select specific expert validator
    - **Client Number**: Filter by patient case number
    - **Disorder**: Filter by psychiatric diagnosis (MDD, BD, OCD, etc.)
    
    **Client-Disorder Mapping:**
    - 6201: MDD (Major Depressive Disorder)
    - 6202: BD (Bipolar Disorder)
    - 6203: PD (Panic Disorder)
    - 6204: GAD (Generalized Anxiety Disorder)
    - 6205: SAD (Social Anxiety Disorder)
    - 6206: OCD (Obsessive-Compulsive Disorder)
    - 6207: PTSD (Post-Traumatic Stress Disorder)
    
    **Usage:**
    1. Use filters to narrow down conversations
    2. Select a conversation from the dropdown
    3. Review the conversation flow between Expert and SP
    4. Export as TXT file for further analysis
    
    **Related Pages:**
    - Page 13: SP Quantitative Validation Data
    - Page 14: SP Qualitative Validation Data
    - Page 16: MFC Viewer (view patient constructs)
    """)
