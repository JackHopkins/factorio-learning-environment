import numpy as np
import pyastar2d


class Node:
    def __init__(self, position, parent=None):
        self.position = position
        self.parent = parent
        self.g = 0
        self.h = 0
        self.f = 0

    def __eq__(self, other):
        return self.position == other.position

def manhattan_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def astar_pathfinding(grid, start, end):
    start_node = Node(start)
    end_node = Node(end)

    open_list = [start_node]
    closed_list = []

    while open_list:
        current_node = min(open_list, key=lambda x: x.f)
        open_list.remove(current_node)
        closed_list.append(current_node)

        if current_node == end_node:
            path = []
            while current_node is not None:
                path.append(current_node.position)
                current_node = current_node.parent
            return path[::-1]

        children = get_neighbors(grid, current_node)

        for child in children:
            if child in closed_list:
                continue

            child.g = current_node.g + 1
            child.h = manhattan_distance(child.position, end_node.position)
            child.f = child.g + child.h

            if any(node in open_list and child.g >= node.g for node in open_list):
                continue

            open_list.append(child)

    return None

def get_closest_valid_point(grid, destination):
    min_dist = float('inf')
    closest_point = None

    for x in range(grid.shape[0]):
        for y in range(grid.shape[1]):
            point_slice = grid[x][y]
            if point_slice == 1:
                dist = manhattan_distance((x, y), destination)
                if dist < min_dist:
                    min_dist = dist
                    closest_point = (x, y)

    return closest_point

def get_neighbors(grid, node):
    neighbors = []
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        x, y = node.position[0] + dx, node.position[1] + dy
        if 0 <= x < grid.shape[1] and 0 <= y < grid.shape[2] and grid[0][x][y] == -1:
            neighbors.append(Node((x, y), parent=node))
    return neighbors

def get_path(end, grid, start = (50, 50)):
    # Sample grid and start/end points
    #end = (end[0]+50, end[1]+50)
    grid = np.array(grid, copy=True)
    grid = np.transpose(grid)
    weights = np.array(grid, dtype=np.float32)

    # Check if the destination is within bounds, otherwise find the closest valid point
    if not (0 <= end[0] < grid.shape[0] and 0 <= end[1] < grid.shape[1]):
        end = get_closest_valid_point(grid, (int(end[0]), int(end[1])))

    # The start and goal coordinates are in matrix coordinates (i, j).
    path = pyastar2d.astar_path(weights, start, (int(end[0]), int(end[1])), allow_diagonal=False)

    # Find the last index where the grid value is not 100
    last_non_100_index = -1
    for idx, coord in enumerate(path):
        value = int(grid[coord[0], coord[1]])
        if value != 100:
            last_non_100_index = idx
        else:
            pass

    # Trim the path
    if last_non_100_index > 0:
        path = path[:last_non_100_index + 1]

    return path


