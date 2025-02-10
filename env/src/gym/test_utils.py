import unittest
from typing import Tuple

import numpy as np
from numpy import ndarray, zeros

from gym.utils import stitch, roll



class TestUtils(unittest.TestCase):

    def setUp(self) -> None:
        bounding_box = 3
        self.grid_world = np.array([[1,2,3],[4,5,6], [7,8,9]], np.int32)

        self.movement_vectors = np.array([(0, 0), (1, 0), (-1, 0), (0, -1), (0, 1)])

        self.rolled_down_fixture = np.array([[7, 8, 9], [1, 2, 3], [4, 5, 6]])
        self.rolled_up_fixture = np.array([[4, 5, 6], [7, 8, 9], [1, 2, 3]])
        self.rolled_left_fixture = np.array([[4, 5, 6], [7, 8, 9], [1, 2, 3]])
        self.rolled_right_fixture = np.array([[4, 5, 6], [7, 8, 9], [1, 2, 3]])

        self.stitched_up_fixture = np.array([[0, 0, 0,], [1, 2, 3,], [4, 5, 6]])
        self.stitched_down_fixture = np.array([[4, 5, 6], [7, 8, 9], [0, 0, 0]])
        self.stitched_left_fixture = np.array([[0, 1, 2], [0, 4, 5], [0, 7, 8]])
        self.stitched_right_fixture = np.array([[2, 3, 0], [5, 6, 0], [8, 9, 0]])
        self.new_field_up = (0, -1)
        self.new_field_down = (0, 1)
        self.new_field_left = (-1, 0)
        self.new_field_right = (1, 0)

        self.new_line = zeros((3, 1))


    def test_row_stitching(self):
        #self.assertEqual(stitch(roll(self.grid_world, self.new_field_up), self.new_line,  self.new_field_up).all(), self.rolled_up_fixture.all())
        self.assertEqual(stitch(self.grid_world, self.new_line, self.new_field_up).all(), self.stitched_up_fixture.all())
        self.assertEqual(stitch(self.grid_world, self.new_line, self.new_field_down).all(), self.stitched_down_fixture.all())
        self.assertEqual(stitch(self.grid_world, self.new_line, self.new_field_left).all(), self.stitched_left_fixture.all())
        self.assertEqual(stitch(self.grid_world, self.new_line, self.new_field_right).all(), self.stitched_right_fixture.all())

    def test_movement_vectors(self):
        self.assertEqual(roll(self.grid_world, self.new_field_up).all(), self.rolled_up_fixture.all())
        self.assertEqual(roll(self.grid_world, self.new_field_down).all(), self.rolled_down_fixture.all())
        self.assertEqual(roll(self.grid_world, self.new_field_left).all(), self.rolled_left_fixture.all())
        self.assertEqual(roll(self.grid_world, self.new_field_right).all(), self.rolled_right_fixture.all())

    def test_rolling(self):
        roll_down = np.roll(self.grid_world, 1, 0)#self.new_field_left)
        self.assertEqual(roll_down.all(), self.rolled_down_fixture.all())
        roll_up = np.roll(self.grid_world, -1, 0)
        self.assertEqual(roll_down.all(), self.rolled_down_fixture.all())
        roll_right = np.roll(self.grid_world, 1, 1)
        self.assertEqual(roll_down.all(), self.rolled_down_fixture.all())
        roll_left = np.roll(self.grid_world, -1, 1)
        self.assertEqual(roll_down.all(), self.rolled_down_fixture.all())

if __name__ == '__main__':
    unittest.main()
