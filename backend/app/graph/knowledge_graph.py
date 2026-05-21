class RepositoryKnowledgeGraph:

    def __init__(self):

        self.nodes = {}

        self.edges = []


    def add_node(

        self,

        node_id,

        node_type,

        metadata
    ):

        self.nodes[node_id] = {

            "type": node_type,

            "metadata": metadata
        }


    def add_edge(

        self,

        source,

        target,

        relationship
    ):

        self.edges.append({

            "source": source,

            "target": target,

            "relationship": relationship
        })


    def get_graph(self):

        return {

            "nodes": self.nodes,

            "edges": self.edges
        }