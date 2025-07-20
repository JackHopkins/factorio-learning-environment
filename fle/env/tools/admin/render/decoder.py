import struct
import zlib
import base64
from typing import Dict, List, Any, Tuple
from collections import defaultdict


class Decoder:
    """Compression utilities for Factorio data transmission for rendering."""

    # Tile type mappings for binary encoding
    TILE_TYPES = {
        'water': 1,
        'deepwater': 2,
        'water-green': 3,
        'water-mud': 4,
        'water-shallow': 5
    }

    TILE_TYPES_REVERSE = {v: k for k, v in TILE_TYPES.items()}

    # Resource type mappings
    RESOURCE_TYPES = {
        'iron-ore': 1,
        'copper-ore': 2,
        'coal': 3,
        'stone': 4,
        'uranium-ore': 5,
        'crude-oil': 6
    }

    RESOURCE_TYPES_REVERSE = {v: k for k, v in RESOURCE_TYPES.items()}

    @classmethod
    def encode_water_binary(cls, water_runs: List[Dict]) -> bytes:
        """
        Encode water runs into a compact binary format.

        Format per run: [type:u8][x:i16][y:i16][length:u8]
        Total: 6 bytes per run vs ~50 bytes JSON
        """
        data = bytearray()

        for run in water_runs:
            tile_type = cls.TILE_TYPES.get(run['t'], 1)
            x = run['x']
            y = run['y']
            length = min(run['l'], 255)  # Cap at 255 for single byte

            # Pack as: unsigned byte, signed short, signed short, unsigned byte
            data.extend(struct.pack('!BhhB', tile_type, x, y, length))

        return bytes(data)

    @classmethod
    def decode_water_binary(cls, data: bytes) -> List[Dict]:
        """Decode binary water data back to run format."""
        runs = []
        offset = 0

        while offset < len(data):
            tile_type, x, y, length = struct.unpack_from('!BhhB', data, offset)
            runs.append({
                't': cls.TILE_TYPES_REVERSE.get(tile_type, 'water'),
                'x': x,
                'y': y,
                'l': length
            })
            offset += 6

        return runs

    @classmethod
    def encode_resources_binary(cls, resource_patches: Dict[str, List[Dict]]) -> bytes:
        """
        Encode resource patches into binary format.

        Format:
        [resource_type:u8][patch_count:u16]
        For each patch:
            [center_x:i16][center_y:i16][entity_count:u16]
            For each entity:
                [dx:i8][dy:i8][amount:u32]
        """
        data = bytearray()

        for resource_name, patches in resource_patches.items():
            resource_type = cls.RESOURCE_TYPES.get(resource_name, 0)
            if resource_type == 0:
                continue

            # Write resource type and patch count
            data.extend(struct.pack('!BH', resource_type, len(patches)))

            for patch in patches:
                center = patch['c']
                entities = patch['e']

                # Write patch header
                data.extend(struct.pack('!hhH', center[0], center[1], len(entities)))

                # Write entities
                for entity in entities:
                    dx = max(-128, min(127, entity[0]))  # Clamp to signed byte range
                    dy = max(-128, min(127, entity[1]))
                    amount = entity[2]
                    data.extend(struct.pack('!bbI', dx, dy, amount))

        return bytes(data)

    @classmethod
    def decode_resources_binary(cls, data: bytes) -> Dict[str, List[Dict]]:
        """Decode binary resource data back to patch format."""
        resources = {}
        offset = 0

        while offset < len(data):
            # Read resource type and patch count
            resource_type, patch_count = struct.unpack_from('!BH', data, offset)
            offset += 3

            resource_name = cls.RESOURCE_TYPES_REVERSE.get(resource_type, 'unknown')
            patches = []

            for _ in range(patch_count):
                # Read patch header
                center_x, center_y, entity_count = struct.unpack_from('!hhH', data, offset)
                offset += 6

                entities = []
                for _ in range(entity_count):
                    dx, dy, amount = struct.unpack_from('!bbI', data, offset)
                    offset += 6
                    entities.append([dx, dy, amount])

                patches.append({
                    'c': [center_x, center_y],
                    'e': entities
                })

            resources[resource_name] = patches

        return resources

    @staticmethod
    def compress_data(data: Dict) -> str:
        """
        Compress the entire data structure using zlib and base64.

        Returns:
            Base64 encoded compressed data
        """
        import json
        json_str = json.dumps(data, separators=(',', ':'))
        compressed = zlib.compress(json_str.encode('utf-8'), level=9)
        return base64.b64encode(compressed).decode('ascii')

    @staticmethod
    def decompress_data(compressed_str: str) -> Dict:
        """
        Decompress base64 encoded zlib compressed data.

        Returns:
            Original data dictionary
        """
        import json
        compressed = base64.b64decode(compressed_str.encode('ascii'))
        json_str = zlib.decompress(compressed).decode('utf-8')
        return json.loads(json_str)

    @staticmethod
    def create_spatial_index(entities: List[Dict], chunk_size: int = 32) -> Dict[Tuple[int, int], List[Dict]]:
        """
        Create a spatial index for entities to enable efficient spatial queries.

        Args:
            entities: List of entities with position data
            chunk_size: Size of each spatial chunk

        Returns:
            Dictionary mapping chunk coordinates to entities in that chunk
        """
        chunks = defaultdict(list)

        for entity in entities:
            pos = entity.get('position', {})
            x = pos.get('x', 0)
            y = pos.get('y', 0)

            chunk_x = int(x // chunk_size)
            chunk_y = int(y // chunk_size)

            chunks[(chunk_x, chunk_y)].append(entity)

        return dict(chunks)

    @staticmethod
    def delta_encode_positions(positions: List[Tuple[int, int]]) -> Dict:
        """
        Delta encode a list of positions for more efficient storage.

        Args:
            positions: List of (x, y) tuples

        Returns:
            Dictionary with start position and list of deltas
        """
        if not positions:
            return {'start': [0, 0], 'deltas': []}

        start = positions[0]
        deltas = []

        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i - 1][0]
            dy = positions[i][1] - positions[i - 1][1]
            deltas.append([dx, dy])

        return {
            'start': list(start),
            'deltas': deltas
        }

    @staticmethod
    def delta_decode_positions(encoded: Dict) -> List[Tuple[int, int]]:
        """Decode delta encoded positions."""
        start = encoded['start']
        deltas = encoded['deltas']

        positions = [(start[0], start[1])]
        x, y = start[0], start[1]

        for dx, dy in deltas:
            x += dx
            y += dy
            positions.append((x, y))

        return positions