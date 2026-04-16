from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


def load_character_file(path: str) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8").strip()

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    try:
        wrapped = "{\n" + raw + "\n}"
        data = json.loads(wrapped)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    raise ValueError(
        f"Could not parse {path} as JSON. "
        "Expected either a JSON object or a name-to-payload mapping."
    )


def unwrap_payload(character_blob: dict[str, Any]) -> dict[str, Any]:
    current: Any = character_blob
    safety = 0

    while isinstance(current, dict) and isinstance(current.get("data"), dict):
        current = current["data"]
        safety += 1
        if safety > 10:
            break

    if not isinstance(current, dict):
        raise ValueError(f"Expected dict payload after unwrapping, got {type(current).__name__}")

    return current


def iter_payloads(raw_data: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    if isinstance(raw_data, dict) and isinstance(raw_data.get("data"), dict):
        payload = unwrap_payload(raw_data)
        yield str(payload.get("name", "Unknown Character")), payload
        return

    for character_name, character_blob in raw_data.items():
        if not isinstance(character_blob, dict):
            continue
        payload = unwrap_payload(character_blob)
        yield character_name, payload


def walk_json(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk_json(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk_json(item)


def iter_spell_entries(node: Any):
    """
    Recursively yields dicts that look like actual spell entries:
    they contain a `definition` dict with a spell name.
    """
    if isinstance(node, dict):
        definition = node.get("definition")
        if isinstance(definition, dict) and definition.get("name"):
            yield node
        else:
            for value in node.values():
                yield from iter_spell_entries(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_spell_entries(item)


def summarize_structure(node: Any, depth: int = 0, max_depth: int = 3) -> str:
    """
    Gives a short structural summary of a nested object.
    """
    if depth > max_depth:
        return "..."

    if isinstance(node, dict):
        keys = list(node.keys())
        preview = ", ".join(map(str, keys[:8]))
        if len(keys) > 8:
            preview += ", ..."
        return f"dict(keys=[{preview}])"

    if isinstance(node, list):
        if not node:
            return "list(empty)"
        first = summarize_structure(node[0], depth + 1, max_depth)
        return f"list(len={len(node)}, first={first})"

    return type(node).__name__


def debug_spell_locations(data: dict[str, Any]) -> None:
    print("\nTop-level keys:")
    print(sorted(data.keys()))

    for root_key in ["spells", "classSpells", "classes"]:
        if root_key in data:
            print(f"\n{root_key!r} structure:")
            print(summarize_structure(data[root_key]))

    if "spells" in data and isinstance(data["spells"], dict):
        print("\nspells buckets:")
        for key, value in data["spells"].items():
            print(f"  spells[{key!r}] -> {summarize_structure(value)}")

    if "classSpells" in data:
        print("\nclassSpells preview:")
        print(summarize_structure(data["classSpells"]))

    if "classes" in data and isinstance(data["classes"], list):
        print("\nclasses spell-related keys:")
        for i, cls in enumerate(data["classes"]):
            if not isinstance(cls, dict):
                continue
            class_name = cls.get("definition", {}).get("name", f"class_{i}")
            spellish_keys = [k for k in cls.keys() if "spell" in str(k).lower()]
            print(f"  {class_name}: {spellish_keys}")


def collect_spells_by_root(data: dict[str, Any]) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}

    candidate_roots = {
        "spells": data.get("spells"),
        "classSpells": data.get("classSpells"),
        "classes": data.get("classes"),
    }

    for root_name, root in candidate_roots.items():
        if root is None:
            continue

        names: list[str] = []
        seen: set[tuple[str, Any]] = set()

        for entry in iter_spell_entries(root):
            definition = entry.get("definition", {})
            spell_name = definition.get("name")
            spell_level = definition.get("level")
            key = (str(spell_name), spell_level)

            if key in seen:
                continue
            seen.add(key)

            names.append(f"{spell_name} (lvl {spell_level})")

        results[root_name] = sorted(names)

    return results


def print_spell_summary(spell_map: dict[str, list[str]]) -> None:
    print("\nSpell summary by root:")
    for root_name, spells in spell_map.items():
        print(f"\n[{root_name}] count={len(spells)}")
        for spell in spells[:25]:
            print(f"  - {spell}")
        if len(spells) > 25:
            print(f"  ... and {len(spells) - 25} more")


def compare_roots(spell_map: dict[str, list[str]]) -> None:
    sets = {k: set(v) for k, v in spell_map.items()}

    if "spells" in sets and "classSpells" in sets:
        only_in_spells = sorted(sets["spells"] - sets["classSpells"])
        only_in_class_spells = sorted(sets["classSpells"] - sets["spells"])

        print("\nComparison: spells vs classSpells")
        print(f"  Only in spells: {len(only_in_spells)}")
        for spell in only_in_spells[:15]:
            print(f"    - {spell}")
        if len(only_in_spells) > 15:
            print(f"    ... and {len(only_in_spells) - 15} more")

        print(f"  Only in classSpells: {len(only_in_class_spells)}")
        for spell in only_in_class_spells[:15]:
            print(f"    - {spell}")
        if len(only_in_class_spells) > 15:
            print(f"    ... and {len(only_in_class_spells) - 15} more")


def main() -> None:
    file_path = "character_sheets.txt"
    raw_data = load_character_file(file_path)

    found_any = False
    for label, payload in iter_payloads(raw_data):
        found_any = True

        print("=" * 100)
        print(f"Character: {payload.get('name')} ({label})")

        debug_spell_locations(payload)
        spell_map = collect_spells_by_root(payload)
        print_spell_summary(spell_map)
        compare_roots(spell_map)

    if not found_any:
        raise ValueError("No valid character payloads found in character_sheets.txt")


if __name__ == "__main__":
    main()