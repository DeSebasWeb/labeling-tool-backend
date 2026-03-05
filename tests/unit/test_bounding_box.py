"""Unit tests — BoundingBox domain entity."""
from __future__ import annotations
import pytest
from src.domain.entities.bounding_box import BoundingBox


class TestBoundingBoxFromPolygon:
    def test_valid_8_floats(self):
        bbox = BoundingBox.from_polygon([0, 0, 10, 0, 10, 5, 0, 5])
        assert bbox.x0 == 0 and bbox.x1 == 10 and bbox.y2 == 5

    def test_wrong_length_raises(self):
        with pytest.raises(ValueError, match="8 valores"):
            BoundingBox.from_polygon([0, 1, 2])

    def test_negative_coord_raises(self):
        with pytest.raises(ValueError, match="negativas"):
            BoundingBox.from_polygon([-1, 0, 10, 0, 10, 5, 0, 5])


class TestBoundingBoxFromRect:
    def test_creates_axis_aligned_quad(self):
        bbox = BoundingBox.from_rect(2, 3, 8, 4)
        assert bbox.x0 == 2 and bbox.y0 == 3
        assert bbox.x1 == 10 and bbox.y1 == 3
        assert bbox.x2 == 10 and bbox.y2 == 7
        assert bbox.x3 == 2 and bbox.y3 == 7

    def test_zero_width_raises(self):
        with pytest.raises(ValueError, match="positivos"):
            BoundingBox.from_rect(0, 0, 0, 5)

    def test_zero_height_raises(self):
        with pytest.raises(ValueError, match="positivos"):
            BoundingBox.from_rect(0, 0, 5, 0)


class TestBoundingBoxToPolygon:
    def test_roundtrip(self):
        coords = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        assert BoundingBox.from_polygon(coords).to_polygon() == coords

    def test_length_is_8(self):
        bbox = BoundingBox.from_rect(0, 0, 100, 200)
        assert len(bbox.to_polygon()) == 8


class TestBoundingBoxMinMax:
    def test_x_min_max(self):
        bbox = BoundingBox.from_rect(5, 10, 20, 30)
        assert bbox.x_min == 5
        assert bbox.x_max == 25

    def test_y_min_max(self):
        bbox = BoundingBox.from_rect(5, 10, 20, 30)
        assert bbox.y_min == 10
        assert bbox.y_max == 40
