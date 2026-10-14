"""Core Content-Addressable Network simulation engine.

The simulator models the standard educational CAN rules: a rectangular 0..100
coordinate space, deterministic key hashing, zone splitting on joins, positive-
length boundary neighbors, and greedy Manhattan-style routing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Dict, List, Optional, Tuple

SPACE_SIZE = 100
Point = Tuple[float, float]


@dataclass
class Zone:
    x1: float
    y1: float
    x2: float
    y2: float
    owner: str

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def center(self) -> Point:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def contains(self, point: Point) -> bool:
        x, y = point
        return self.x1 <= x < self.x2 and self.y1 <= y < self.y2

    def distance_to(self, point: Point) -> float:
        """Minimum Manhattan distance from a point to this rectangle."""
        x, y = point
        dx = max(self.x1 - x, 0, x - self.x2)
        dy = max(self.y1 - y, 0, y - self.y2)
        return dx + dy


@dataclass
class Peer:
    peer_id: str
    zone: Zone
    data: Dict[str, str] = field(default_factory=dict)
    neighbors: List[str] = field(default_factory=list)


class CANNetwork:
    """In-memory CAN overlay with deterministic, testable operations."""

    def __init__(self, peer_count: int = 4):
        self.peers: Dict[str, Peer] = {}
        self.lookup_history: List[dict] = []
        self.successful_lookups = 0
        self.failed_lookups = 0
        self.total_hops = 0
        self.next_peer_number = 1
        self.initialize(peer_count)

    def initialize(self, peer_count: int = 4) -> None:
        if peer_count < 1:
            raise ValueError("peer_count must be at least 1")
        self.peers.clear()
        self.lookup_history.clear()
        self.successful_lookups = self.failed_lookups = self.total_hops = 0
        self.next_peer_number = 1
        self._create_peer("P1", Zone(0, 0, SPACE_SIZE, SPACE_SIZE, "P1"))
        for _ in range(peer_count - 1):
            self.add_peer()
        self._refresh_neighbors()

    def _new_id(self) -> str:
        while f"P{self.next_peer_number}" in self.peers:
            self.next_peer_number += 1
        result = f"P{self.next_peer_number}"
        self.next_peer_number += 1
        return result

    def _create_peer(self, peer_id: str, zone: Zone) -> Peer:
        peer = Peer(peer_id, zone)
        self.peers[peer_id] = peer
        return peer

    @property
    def zones(self) -> List[Zone]:
        return [peer.zone for peer in self.peers.values()]

    def _refresh_neighbors(self) -> None:
        for peer in self.peers.values():
            peer.neighbors = []
        ids = list(self.peers)
        for index, left_id in enumerate(ids):
            for right_id in ids[index + 1 :]:
                if self._share_positive_boundary(self.peers[left_id].zone, self.peers[right_id].zone):
                    self.peers[left_id].neighbors.append(right_id)
                    self.peers[right_id].neighbors.append(left_id)
        for peer in self.peers.values():
            peer.neighbors.sort()

    @staticmethod
    def _share_positive_boundary(a: Zone, b: Zone) -> bool:
        vertical = (a.x2 == b.x1 or b.x2 == a.x1) and min(a.y2, b.y2) > max(a.y1, b.y1)
        horizontal = (a.y2 == b.y1 or b.y2 == a.y1) and min(a.x2, b.x2) > max(a.x1, b.x1)
        return vertical or horizontal

    def add_peer(self, peer_id: Optional[str] = None, split_peer_id: Optional[str] = None) -> Peer:
        """Split a zone along its longest dimension and return the new peer."""
        if not self.peers:
            pid = peer_id or self._new_id()
            return self._create_peer(pid, Zone(0, 0, SPACE_SIZE, SPACE_SIZE, pid))
        if peer_id and peer_id in self.peers:
            raise ValueError(f"Peer {peer_id} already exists")
        source = self.peers.get(split_peer_id) if split_peer_id else max(
            self.peers.values(), key=lambda p: (p.zone.width * p.zone.height, p.peer_id)
        )
        if source is None:
            raise ValueError("The selected split peer does not exist")
        zone = source.zone
        if zone.width <= 1 and zone.height <= 1:
            raise ValueError("Selected zone is too small to split")
        new_id = peer_id or self._new_id()
        if zone.width >= zone.height:
            cut = zone.x1 + zone.width / 2
            old_zone = Zone(zone.x1, zone.y1, cut, zone.y2, source.peer_id)
            new_zone = Zone(cut, zone.y1, zone.x2, zone.y2, new_id)
        else:
            cut = zone.y1 + zone.height / 2
            old_zone = Zone(zone.x1, zone.y1, zone.x2, cut, source.peer_id)
            new_zone = Zone(zone.x1, cut, zone.x2, zone.y2, new_id)
        source.zone = old_zone
        # Existing records stay with the old half unless they belong geometrically
        # to the new half; those records are transferred to the joining peer.
        new_peer = self._create_peer(new_id, new_zone)
        moved = {key: value for key, value in source.data.items() if new_zone.contains(self.key_to_coordinate(key))}
        for key in moved:
            del source.data[key]
        new_peer.data.update(moved)
        self._refresh_neighbors()
        return new_peer

    @staticmethod
    def key_to_coordinate(key: str) -> Point:
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        x = int.from_bytes(digest[:8], "big") / 2**64 * SPACE_SIZE
        y = int.from_bytes(digest[8:16], "big") / 2**64 * SPACE_SIZE
        return round(x, 3), round(y, 3)

    def owner_for_point(self, point: Point) -> Optional[Peer]:
        return next((peer for peer in self.peers.values() if peer.zone.contains(point)), None)

    def owner_for_key(self, key: str) -> Optional[Peer]:
        return self.owner_for_point(self.key_to_coordinate(key))

    def store(self, key: str, value: str) -> Tuple[Point, str]:
        key = key.strip()
        if not key:
            raise ValueError("Key cannot be empty")
        target = self.owner_for_key(key)
        if target is None:
            raise RuntimeError("No peer owns the mapped coordinate")
        # A key is unique in a CAN. Remove stale copies before writing the value.
        for peer in self.peers.values():
            peer.data.pop(key, None)
        target.data[key] = value
        return self.key_to_coordinate(key), target.peer_id

    def find_key(self, key: str) -> Optional[Tuple[str, str]]:
        target = self.owner_for_key(key)
        if target and key in target.data:
            return target.peer_id, target.data[key]
        return None

    def route(self, key: str, start_peer_id: Optional[str] = None) -> dict:
        """Greedily route to the responsible zone, with loop protection.

        ``success`` means the route reached the responsible zone. ``found``
        separately reports whether that zone contains the requested key.
        """
        if not self.peers:
            raise RuntimeError("Network is empty")
        point = self.key_to_coordinate(key)
        destination = self.owner_for_point(point)
        current = self.peers.get(start_peer_id) if start_peer_id else self.peers[sorted(self.peers)[0]]
        if current is None:
            raise ValueError("Starting peer does not exist")
        path = [current.peer_id]
        visited = {current.peer_id}
        failure_reason = None
        while not current.zone.contains(point):
            candidates = [self.peers[n] for n in current.neighbors if n not in visited]
            candidates = [p for p in candidates if p.zone.distance_to(point) < current.zone.distance_to(point)]
            if not candidates:
                failure_reason = "No unvisited neighbor is closer to the destination"
                break
            current = min(candidates, key=lambda p: (p.zone.distance_to(point), p.peer_id))
            path.append(current.peer_id)
            visited.add(current.peer_id)
        success = destination is not None and current.peer_id == destination.peer_id
        if not success and failure_reason is None:
            failure_reason = "Destination zone could not be reached"
        found = bool(destination and key in destination.data)
        result = {
            "key": key, "coordinate": point, "path": path,
            "hops": max(0, len(path) - 1), "success": success,
            "found": found,
            "destination": destination.peer_id if destination else None,
            "value": destination.data.get(key) if found and destination else None,
            "reason": failure_reason,
        }
        self.total_hops += result["hops"]
        if success:
            self.successful_lookups += 1
        else:
            self.failed_lookups += 1
        self.lookup_history.insert(0, result)
        self.lookup_history = self.lookup_history[:30]
        return result

    def remove_peer(self, peer_id: str) -> dict:
        """Remove a peer while preserving a gap-free, non-overlapping partition.

        If an adjacent zone can absorb the departing rectangle as one rectangle,
        merge it. Otherwise, rebuild the remaining rectangular partition and
        redistribute records. This fallback preserves exact coverage even when
        no single adjacent rectangle can absorb the departing zone.
        """
        if peer_id not in self.peers:
            raise ValueError(f"Peer {peer_id} does not exist")
        if len(self.peers) == 1:
            raise ValueError("The last peer cannot be removed")
        departing = self.peers[peer_id]
        neighbors = [self.peers[n] for n in departing.neighbors]
        if not neighbors:
            raise RuntimeError("Cannot remove an isolated peer")
        merge_target = next((p for p in neighbors if self._mergeable(p.zone, departing.zone)), None)
        target = merge_target or min(neighbors, key=lambda p: (p.zone.width * p.zone.height, p.peer_id))
        reassigned = dict(departing.data)
        if merge_target:
            target.zone = self._merged_zone(target.zone, departing.zone, target.peer_id)
        else:
            # An arbitrary non-mergeable departure is rebuilt as a fresh
            # rectangular partition so no zone is silently lost.
            all_data = {key: value for peer in self.peers.values() for key, value in peer.data.items()}
            del self.peers[peer_id]
            remaining_ids = sorted(self.peers)
            self.peers = {}
            self._create_peer(remaining_ids[0], Zone(0, 0, SPACE_SIZE, SPACE_SIZE, remaining_ids[0]))
            for remaining_id in remaining_ids[1:]:
                self.add_peer(peer_id=remaining_id)
            for key, value in all_data.items():
                target_peer = self.owner_for_key(key)
                if target_peer:
                    target_peer.data[key] = value
            self._refresh_neighbors()
            return {"removed": peer_id, "assigned_to": "rebalanced network", "merged": False, "keys_moved": len(reassigned)}
        del self.peers[peer_id]
        if merge_target:
            target.data.update(reassigned)
        self._refresh_neighbors()
        return {"removed": peer_id, "assigned_to": target.peer_id, "merged": bool(merge_target), "keys_moved": len(reassigned)}

    @staticmethod
    def _mergeable(a: Zone, b: Zone) -> bool:
        same_horizontal = a.y1 == b.y1 and a.y2 == b.y2 and (a.x2 == b.x1 or b.x2 == a.x1)
        same_vertical = a.x1 == b.x1 and a.x2 == b.x2 and (a.y2 == b.y1 or b.y2 == a.y1)
        return same_horizontal or same_vertical

    @staticmethod
    def _merged_zone(a: Zone, b: Zone, owner: str) -> Zone:
        return Zone(min(a.x1, b.x1), min(a.y1, b.y1), max(a.x2, b.x2), max(a.y2, b.y2), owner)

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.peers:
            return ["Network has no peers"]
        area = sum(peer.zone.width * peer.zone.height for peer in self.peers.values())
        if round(area, 6) != SPACE_SIZE * SPACE_SIZE:
            errors.append(f"Zone area is {area}, expected {SPACE_SIZE * SPACE_SIZE}")
        ids = list(self.peers)
        for i, left_id in enumerate(ids):
            for right_id in ids[i + 1 :]:
                a, b = self.peers[left_id].zone, self.peers[right_id].zone
                overlap_w = min(a.x2, b.x2) - max(a.x1, b.x1)
                overlap_h = min(a.y2, b.y2) - max(a.y1, b.y1)
                if overlap_w > 0 and overlap_h > 0:
                    errors.append(f"Zones {left_id} and {right_id} overlap")
        for peer in self.peers.values():
            if not (0 <= peer.zone.x1 < peer.zone.x2 <= SPACE_SIZE and 0 <= peer.zone.y1 < peer.zone.y2 <= SPACE_SIZE):
                errors.append(f"Zone for {peer.peer_id} is outside the coordinate space")
            expected = sorted(n.peer_id for n in self.peers.values() if n.peer_id != peer.peer_id and self._share_positive_boundary(peer.zone, n.zone))
            if sorted(peer.neighbors) != expected:
                errors.append(f"Neighbor list for {peer.peer_id} is stale")
        return errors

    @property
    def average_hops(self) -> float:
        count = self.successful_lookups + self.failed_lookups
        return self.total_hops / count if count else 0.0
