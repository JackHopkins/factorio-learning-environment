import numpy as np


def _create_label_to_integer_mapping(labeled_matrix, original_matrix):
    label_to_integer = {}
    unique_labels = np.unique(labeled_matrix)

    for label in unique_labels:
        # Find the mask where the labeled_matrix has the current label
        label_mask = (labeled_matrix == label)

        # Get the unique integer values from the original matrix corresponding to the current label
        unique_values = np.unique(original_matrix[label_mask])

        # Assuming that there's only one unique integer value in the group
        original_integer = unique_values[0]
        label_to_integer[label] = original_integer

    return label_to_integer


def _get_min_offsets(matrix, point):
    labeled_groups = np.unique(matrix)
    min_offsets = {}
    min_location = {}
    for label in labeled_groups:
        if label == 0:
            continue  # Skip background label

        # Get the coordinates of all points in the current labeled group
        group_points = np.argwhere(matrix == label)

        # Calculate the x and y offsets between the given point and all points in the group
        offsets = group_points - point

        # Get the smallest x and y offsets for the current group
        min_offsets[label] = np.min(np.abs(offsets), axis=0)
        min_location[label] = np.min(offsets, axis=0)

    return min_offsets

