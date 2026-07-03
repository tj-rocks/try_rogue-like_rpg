from collections import Counter


class TacticalProfile:
    def __init__(self, data=None):
        self.counter = Counter(data or {})

    def _key(self, relation, distance, action):
        return f"{relation}|{distance}|{action}"

    def record(self, relation, distance, action):
        if not relation or not distance or not action:
            return
        self.counter[self._key(relation, distance, action)] += 1

    def get_distribution(self, relation, distance):
        result = {}
        prefix = f"{relation}|{distance}|"
        for key, count in self.counter.items():
            if key.startswith(prefix):
                action = key.split("|")[2]
                result[action] = count
        return result

    def get_preferred_action(self, relation, distance):
        dist = self.get_distribution(relation, distance)
        if not dist:
            return None
        return max(dist.items(), key=lambda x: x[1])[0]

    def get_action_total(self, action, relation=None, distance=None):
        total = 0
        for key, count in self.counter.items():
            key_relation, key_distance, key_action = key.split("|", 2)
            if key_action != action:
                continue
            if relation is not None and key_relation != relation:
                continue
            if distance is not None and key_distance != distance:
                continue
            total += count
        return total

    def get_action_probability(self, action, relation=None, distance=None, smoothing=1.0, default=0.0):
        dist = self.get_distribution(relation, distance) if relation is not None and distance is not None else {}
        total = sum(dist.values())
        if total <= 0:
            return default
        action_count = dist.get(action, 0)
        denom = total + smoothing * max(1, len(dist))
        return (action_count + smoothing) / denom

    def to_dict(self):
        return dict(self.counter)

    @classmethod
    def from_dict(cls, data):
        return cls(data or {})


def get_relation_and_distance(player, enemy, tile_size):
    px = int((player.x + player.width / 2) // tile_size)
    py = int((player.y + player.height / 2) // tile_size)
    ex = int((enemy.x + enemy.width / 2) // tile_size)
    ey = int((enemy.y + enemy.height / 2) // tile_size)
    return get_relation_and_distance_from_tiles(px, py, ex, ey)


def get_relation_and_distance_from_tiles(px, py, ex, ey):
    dx = px - ex
    dy = py - ey
    dist = max(abs(dx), abs(dy))

    if dist >= 3:
        distance = "3plus"
    elif dist == 2:
        distance = "2"
    else:
        distance = "1"

    if dist >= 3:
        relation = "far"
    elif dx == 0 or dy == 0:
        relation = "front"
    elif abs(dx) == abs(dy):
        relation = "diagonal"
    else:
        relation = "side"

    return relation, distance
