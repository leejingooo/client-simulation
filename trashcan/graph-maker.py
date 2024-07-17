import streamlit as st
import networkx as nx
import json
from pyvis.network import Network
import streamlit.components.v1 as components


def create_graph():
    return nx.Graph()


def add_node(G, node_id):
    G.add_node(node_id)


def add_edge(G, source, target):
    G.add_edge(source, target)


def graph_to_json(G):
    return json.dumps(nx.node_link_data(G))


def visualize_graph(G):
    net = Network(notebook=True, width="100%", height="400px")
    net.from_nx(G)
    net.toggle_physics(False)
    net.show("graph.html")

    with open("graph.html", "r", encoding="utf-8") as f:
        html = f.read()

    components.html(html, height=400)


def main():
    st.title("Interactive Graph Creator")

    # Initialize session state
    if 'graph' not in st.session_state:
        st.session_state.graph = create_graph()

    # Node creation
    st.subheader("Add Node")
    node_id = st.text_input("Node Name")
    if st.button("Add Node"):
        if node_id:
            add_node(st.session_state.graph, node_id)
            st.success(f"Node '{node_id}' added successfully!")
        else:
            st.warning("Please enter a node name.")

    # Edge creation
    st.subheader("Add Edge")
    nodes = list(st.session_state.graph.nodes())
    if len(nodes) >= 2:
        source = st.selectbox("From", nodes, key="source")
        target = st.selectbox("To", nodes, key="target")
        if st.button("Connect Nodes"):
            add_edge(st.session_state.graph, source, target)
            st.success(
                f"Edge between '{source}' and '{target}' added successfully!")
    else:
        st.info("Add at least two nodes to create edges.")

    # Visualize the graph
    st.subheader("Graph Visualization")
    visualize_graph(st.session_state.graph)

    # Show JSON representation
    st.subheader("JSON Representation")
    json_data = graph_to_json(st.session_state.graph)
    st.json(json_data)


if __name__ == "__main__":
    main()
