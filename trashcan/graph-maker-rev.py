import streamlit as st
from pyvis.network import Network
import networkx as nx
import json

# Initialize the session state for the graph and JSON
if 'graph' not in st.session_state:
    st.session_state.graph = nx.Graph()

if 'json_data' not in st.session_state:
    st.session_state.json_data = {
        "Identification": {
            "Gender": "string",
            "Age": "number",
            "Marital status": "string",
            "Siblings": "string",
            "Birthplace": "string",
            "Residence": "string",
            "Occupation": "string"
        },
        "Patient history": {
            "Birth": "string",
            "Development": "string",
            "Recent history": "string"
        },
        "C.C/Duration": {
            "Symptoms": [
                "string"
            ],
            "Duration": "string"
        },
        "Mental Status Examination": {
            "Mood": "string",
            "Affect": "string",
            "Psychomotor retardation": "boolean",
            "Suicidal ideation": "boolean"
        },
        "Psychodynamic formulation": {
            "Defense mechanisms": [
                "string"
            ],
            "Attachment": "string"
        }
    }

# Function to update JSON from graph


def update_json_from_graph():
    new_json = {}
    for node in st.session_state.graph.nodes:
        new_json[node] = st.session_state.json_data.get(node, {})
    st.session_state.json_data = new_json

# Function to update graph from JSON


def update_graph_from_json():
    st.session_state.graph.clear()
    for category, subcategories in st.session_state.json_data.items():
        st.session_state.graph.add_node(category, label=category)
        if isinstance(subcategories, dict):
            for subcategory, value in subcategories.items():
                st.session_state.graph.add_node(
                    f"{category}_{subcategory}", label=subcategory)
                st.session_state.graph.add_node(
                    f"{category}_{subcategory}_value", label=str(value))
                st.session_state.graph.add_edge(
                    category, f"{category}_{subcategory}")
                st.session_state.graph.add_edge(
                    f"{category}_{subcategory}", f"{category}_{subcategory}_value")
        elif isinstance(subcategories, list):
            for item in subcategories:
                st.session_state.graph.add_node(
                    f"{category}_{item}", label=str(item))
                st.session_state.graph.add_edge(category, f"{category}_{item}")

# Function to save JSON and Graph to file


def save_graph_and_json():
    with open('graph.json', 'w') as f:
        json.dump(st.session_state.json_data, f)
    nx.write_gpickle(st.session_state.graph, 'graph.gpickle')

# Function to load JSON and Graph from file


def load_graph_and_json(json_file, graph_file):
    with open(json_file) as f:
        st.session_state.json_data = json.load(f)
    st.session_state.graph = nx.read_gpickle(graph_file)
    update_graph_from_json()

# Render the graph using PyVis


def render_graph():
    net = Network(height="750px", width="100%",
                  bgcolor="#222222", font_color="white")
    for node, data in st.session_state.graph.nodes(data=True):
        net.add_node(node, label=data.get('label', node))
    for edge in st.session_state.graph.edges:
        net.add_edge(edge[0], edge[1])

    net.show_buttons(filter_=['physics'])
    net.save_graph("pyvis_graph.html")
    with open("pyvis_graph.html", "r") as f:
        html = f.read()
    return html


# Main app
st.title("Interactive Graph and JSON Editor")

# JSON editing section
st.header("JSON Representation")
json_text = st.text_area("Edit JSON", value=json.dumps(
    st.session_state.json_data, indent=2), height=400)
try:
    updated_json = json.loads(json_text)
    st.session_state.json_data = updated_json
    update_graph_from_json()
except json.JSONDecodeError:
    st.error("Invalid JSON format")

# Graph rendering section
st.header("Graph Representation")
graph_html = render_graph()
st.components.v1.html(graph_html, height=800)

# Save and Load functionality
st.header("Save/Load Graph and JSON")
if st.button("Save Graph and JSON"):
    save_graph_and_json()
    st.success("Graph and JSON saved!")

uploaded_json_file = st.file_uploader("Upload JSON file", type="json")
uploaded_graph_file = st.file_uploader("Upload Graph file", type="gpickle")

if st.button("Load Graph and JSON"):
    if uploaded_json_file is not None and uploaded_graph_file is not None:
        load_graph_and_json(uploaded_json_file, uploaded_graph_file)
        st.success("Graph and JSON loaded!")
    else:
        st.error("Please upload both JSON and Graph files")

# Instructions for modifying the graph
st.header("Instructions")
st.write("""
1. Right-click on the graph to modify nodes.
2. Select "connect/add/delete/modify" to modify the node.
3. Nodes will change color during the connection process, and the edge will turn black once connected.
""")
