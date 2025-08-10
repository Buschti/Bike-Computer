from heapq import heappush, heappop

from Graphs import Graph, Node
from Util.Haversine import Haversine


class AStar:
    """
    A class to represent the A* pathfinding algorithm.

    This class implements the A* pathfinding algorithm, which is used to find the shortest path between two nodes in
    a graph. The algorithm uses a heuristic to estimate the cost of the path from a given node to the goal node, and
    it uses a priority queue to explore the nodes with the lowest total cost first.

    Attributes:
        haversine (Haversine): An instance of the Haversine class to calculate distances.
        graph (Graph): The graph on which the algorithm operates.

    Methods:
        __init__(graph): Constructs an AStar object for the given graph.
        heuristic(node, goal): Calculates the heuristic value for a given node with respect to the goal node.
        reconstruct_path(came_from, start, goal): Reconstructs the shortest path from start node to goal node.
        search(start_node, goal_node): Executes the A* search algorithm from the start node to the goal node.
    """
    haversine = Haversine()

    def __init__(self, graph: Graph):
        self.graph = graph

    def heuristic(self, node: Node, goal: Node) -> float:
        """
        Calculates the heuristic value for a given node with respect to the goal node.

        This method uses the Haversine formula to calculate the great-circle distance between two points – that is, the
        shortest distance over the earth's surface – giving an "as-the-crow-flies" distance between the points
         (ignoring any hills, valleys, or other potential obstacles).
         #TODO atm this is a good start, maybe it should be changed it the future for a better heuristic

        :param: node (Node): The node for which the heuristic value is to be calculated.
        :param: goal (Node): The goal node in reference to which the heuristic value is calculated.

        :return float: The heuristic value of the node.
            """
        return (self.haversine.haversine(node.latitude, node.longitude, goal.latitude, goal.longitude)) / 2

    def reconstruct_path(self, came_from: dict, start: Node, goal: Node) -> list:
        """
        Reconstructs the shortest path from start node to goal node.

        This method is used after the search method has been executed, to trace back the path from the goal node to the
         start node. It uses the 'came_from' dictionary which keeps track of the node from which we arrived at a
         particular node during the search.

        :param: came_from (dict): A dictionary where the keys are nodes and the values are the nodes from which we
                arrived at the key node.
        :return list: A list of nodes representing the shortest path from start to goal. The list is ordered from start
                        to goal.
        """
        current = goal
        path = []
        while current != start:
            path.append(current)
            current = came_from[current]
        path.append(start)
        return path[::-1]

    def search(self, start_node: Node, goal_node: Node) -> (list, dict):
        """
        A* is a graph traversal and pathfinding algorithm, which is used in many fields of
        computer science due to its completeness, optimality, and optimal efficiency. Given a weighted graph,
        a source node and a goal node, the algorithm finds the shortest path (with respect to the given weights) from
        source to goal
        :return: The shortest path and its length in meters
        # TODO length in meters is not necessary, it was used for testing
        """
        came_from = {}
        cost_so_far = {start_node: 0}
        cost_so_far_meters = {start_node: 0}
        priority_queue = [(0, start_node)]
        while priority_queue:
            current_cost, current_node = heappop(priority_queue)

            if current_node == goal_node:
                return self.reconstruct_path(came_from, start_node, goal_node), cost_so_far_meters[
                    goal_node]

            for edge in self.graph.get_neighbors(current_node):
                neighbor = edge.target
                new_cost = cost_so_far[current_node] + edge.weight
                new_cost_meters = cost_so_far_meters[current_node] + edge.weight

                if neighbor not in cost_so_far or new_cost < cost_so_far[neighbor]:
                    cost_so_far[neighbor] = new_cost
                    cost_so_far_meters[neighbor] = new_cost_meters
                    priority = new_cost + self.heuristic(neighbor, goal_node)
                    heappush(priority_queue, (priority, neighbor))
                    came_from[neighbor] = current_node

        return None, None
