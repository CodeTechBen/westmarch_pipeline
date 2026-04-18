from __future__ import annotations

import logging
import re
from os import environ as ENV
from typing import Any, Optional

import requests


STAT_ID_TO_NAME: dict[int, str] = {
    1: "strength",
    2: "dexterity",
    3: "constitution",
    4: "intelligence",
    5: "wisdom",
    6: "charisma",
}

STAT_SUBTYPE_TO_NAME: dict[str, str] = {
    "strength-score": "strength",
    "dexterity-score": "dexterity",
    "constitution-score": "constitution",
    "intelligence-score": "intelligence",
    "wisdom-score": "wisdom",
    "charisma-score": "charisma",
}


def safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    return default


def ability_mod(score: int) -> int:
    return (score - 10) // 2


def get_proficiency_bonus(level: int) -> int:
    if level >= 17:
        return 6
    if level >= 13:
        return 5
    if level >= 9:
        return 4
    if level >= 5:
        return 3
    return 2


def walk_json(node: Any):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk_json(value)
    elif isinstance(node, list):
        for item in node:
            yield from walk_json(item)


def get_total_level(data: dict[str, Any]) -> int:
    return sum(
        safe_int(cls.get("level"))
        for cls in data.get("classes", [])
        if isinstance(cls, dict)
    )


def get_base_stats(data: dict[str, Any]) -> dict[str, int]:
    base = {name: 0 for name in STAT_ID_TO_NAME.values()}

    for stat in data.get("stats", []):
        if not isinstance(stat, dict):
            continue
        stat_id = stat.get("id")
        if stat_id in STAT_ID_TO_NAME:
            base[STAT_ID_TO_NAME[stat_id]] = safe_int(stat.get("value"))

    return base


def get_component_name_map(data: dict[str, Any]) -> dict[str, str]:
    raw_map = data.get("definitionKeyNameMap", {})
    if isinstance(raw_map, dict):
        return {str(k): str(v) for k, v in raw_map.items()}
    return {}


def get_notes_text(data: dict[str, Any]) -> str:
    notes = data.get("notes", {})
    if not isinstance(notes, dict):
        return ""

    parts: list[str] = []
    for value in notes.values():
        if isinstance(value, str) and value.strip():
            parts.append(value.lower())

    return "\n".join(parts)


def collect_modifiers(data: dict[str, Any]) -> list[dict[str, Any]]:
    modifiers: list[dict[str, Any]] = []

    for obj in walk_json(data):
        modifier_type = obj.get("type")
        subtype = obj.get("subType")

        if not isinstance(modifier_type, str) or not isinstance(subtype, str):
            continue

        if modifier_type not in {
            "bonus",
            "proficiency",
            "expertise",
            "half-proficiency",
        }:
            continue

        modifiers.append(obj)

    return modifiers


def resolve_ability_bonuses(
    modifiers: list[dict[str, Any]],
    component_name_map: dict[str, str],
) -> tuple[list[dict[str, Any]], list[str]]:
    found: list[dict[str, Any]] = []
    debug_lines: list[str] = []

    for mod in modifiers:
        subtype = mod.get("subType")
        if subtype not in STAT_SUBTYPE_TO_NAME:
            continue

        stat_name = STAT_SUBTYPE_TO_NAME[subtype]
        value = safe_int(mod.get("value"), safe_int(mod.get("fixedValue")))
        component_id = mod.get("componentId")

        source_name = None
        if component_id is not None:
            source_name = component_name_map.get(f"feat:{component_id}")

        record = {
            "stat": stat_name,
            "subType": subtype,
            "value": value,
            "componentId": component_id,
            "source_name": source_name,
        }
        found.append(record)

        source = source_name or f"componentId={component_id}"
        debug_lines.append(f"{stat_name}: +{value} from {source}")

    return found, debug_lines


def apply_ability_bonuses(
    base_stats: dict[str, int],
    bonuses: list[dict[str, Any]],
) -> dict[str, int]:
    final_stats = base_stats.copy()

    for bonus in bonuses:
        stat = bonus["stat"]
        final_stats[stat] += safe_int(bonus["value"])

    return final_stats


def get_active_set_stat_modifiers(data: dict[str, Any]) -> dict[str, tuple[int, str]]:
    active_sets: dict[str, tuple[int, str]] = {}

    for item in data.get("inventory", []):
        if not isinstance(item, dict):
            continue
        if not item.get("equipped"):
            continue

        is_attuned = bool(item.get("isAttuned"))
        definition = item.get("definition", {})
        if not isinstance(definition, dict):
            continue

        item_name = definition.get("name", "Unknown Item")

        for mod in definition.get("grantedModifiers", []):
            if not isinstance(mod, dict):
                continue
            if mod.get("type") != "set":
                continue

            subtype = mod.get("subType")
            if subtype not in STAT_SUBTYPE_TO_NAME:
                continue

            requires_attunement = bool(mod.get("requiresAttunement"))
            if requires_attunement and not is_attuned:
                continue

            value = mod.get("value")
            if not isinstance(value, (int, float)):
                value = mod.get("fixedValue")

            if not isinstance(value, (int, float)):
                continue

            stat_name = STAT_SUBTYPE_TO_NAME[subtype]
            numeric_value = int(value)

            existing = active_sets.get(stat_name)
            if existing is None or numeric_value > existing[0]:
                active_sets[stat_name] = (numeric_value, item_name)

    return active_sets


def apply_set_stat_modifiers(
    final_stats: dict[str, int],
    active_sets: dict[str, tuple[int, str]],
) -> tuple[dict[str, int], list[str]]:
    updated = final_stats.copy()
    debug_lines: list[str] = []

    for stat_name, (set_value, source_name) in active_sets.items():
        if updated[stat_name] < set_value:
            old_value = updated[stat_name]
            updated[stat_name] = set_value
            debug_lines.append(f"{stat_name}: set from {old_value} to {set_value} by {source_name}")

    return updated, debug_lines


def has_tough_feat(data: dict[str, Any], component_name_map: dict[str, str]) -> bool:
    for feat_name in component_name_map.values():
        if feat_name.strip().lower() == "tough":
            return True

    for obj in walk_json(data):
        name = obj.get("name")
        if isinstance(name, str) and name.strip().lower() == "tough":
            return True

    return "tough feat" in get_notes_text(data)


def get_skill_multiplier(modifiers: list[dict[str, Any]], skill_name: str) -> float:
    skill_name = skill_name.lower()
    multiplier = 0.0

    for mod in modifiers:
        mod_type = mod.get("type")
        subtype = mod.get("subType")

        if subtype not in {skill_name, "ability-checks"}:
            continue

        if mod_type == "expertise" and subtype == skill_name:
            return 2.0

        if mod_type == "proficiency" and subtype == skill_name:
            multiplier = max(multiplier, 1.0)

        if mod_type == "half-proficiency":
            if subtype == skill_name or subtype == "ability-checks":
                multiplier = max(multiplier, 0.5)

    return multiplier


def get_armor_category(definition: dict[str, Any]) -> str:
    armor_type_id = definition.get("armorTypeId")
    if armor_type_id == 1:
        return "light"
    if armor_type_id == 2:
        return "medium"
    if armor_type_id == 3:
        return "heavy"
    if armor_type_id == 4:
        return "shield"

    armor_type_text = str(definition.get("type") or "").lower()
    if "light" in armor_type_text:
        return "light"
    if "medium" in armor_type_text:
        return "medium"
    if "heavy" in armor_type_text:
        return "heavy"
    if "shield" in armor_type_text:
        return "shield"

    base_name = str(definition.get("baseArmorName") or "").lower()
    if base_name == "shield":
        return "shield"
    if base_name in {"leather", "studded leather", "padded"}:
        return "light"
    if base_name in {"hide", "chain shirt", "scale mail", "breastplate", "half plate"}:
        return "medium"
    if base_name in {"ring mail", "chain mail", "splint", "plate"}:
        return "heavy"

    return "unknown"


def get_equipped_body_armor(data: dict[str, Any]) -> dict[str, Any] | None:
    for item in data.get("inventory", []):
        if not isinstance(item, dict) or not item.get("equipped"):
            continue

        definition = item.get("definition", {})
        if not isinstance(definition, dict):
            continue

        if definition.get("filterType") != "Armor":
            continue

        if get_armor_category(definition) == "shield":
            continue

        return item

    return None


def get_equipped_shield(data: dict[str, Any]) -> dict[str, Any] | None:
    for item in data.get("inventory", []):
        if not isinstance(item, dict) or not item.get("equipped"):
            continue

        definition = item.get("definition", {})
        if not isinstance(definition, dict):
            continue

        if definition.get("filterType") != "Armor":
            continue

        if get_armor_category(definition) == "shield":
            return item

    return None


def get_item_ac_bonus(item: dict[str, Any]) -> tuple[int, list[str]]:
    total_bonus = 0
    reasons: list[str] = []

    is_attuned = bool(item.get("isAttuned"))
    definition = item.get("definition", {})
    if not isinstance(definition, dict):
        return 0, reasons

    item_name = definition.get("name", "Unknown Item")

    for mod in definition.get("grantedModifiers", []):
        if not isinstance(mod, dict):
            continue

        if mod.get("type") != "bonus" or mod.get("subType") != "armor-class":
            continue

        requires_attunement = bool(mod.get("requiresAttunement"))
        if requires_attunement and not is_attuned:
            continue

        value = mod.get("value")
        if not isinstance(value, (int, float)):
            value = mod.get("fixedValue")

        if not isinstance(value, (int, float)):
            continue

        numeric_value = int(value)
        total_bonus += numeric_value
        reasons.append(f"{item_name}: +{numeric_value} AC")

    return total_bonus, reasons


def calculate_armor_class(data: dict[str, Any], final_stats: dict[str, int]) -> tuple[int, str]:
    dex_mod = ability_mod(final_stats["dexterity"])
    reason_parts: list[str] = []

    body_armor = get_equipped_body_armor(data)
    shield = get_equipped_shield(data)

    if body_armor is None:
        total_ac = 10 + dex_mod
        reason_parts.append(f"no armor: 10 + DEX mod {dex_mod}")
    else:
        definition = body_armor.get("definition", {})
        armor_name = definition.get("name", "Unknown Armor")
        base_ac = safe_int(definition.get("armorClass"), 10)
        category = get_armor_category(definition)

        if category == "light":
            total_ac = base_ac + dex_mod
            reason_parts.append(f"{armor_name}: {base_ac} + DEX mod {dex_mod}")
        elif category == "medium":
            dex_part = min(dex_mod, 2)
            total_ac = base_ac + dex_part
            reason_parts.append(f"{armor_name}: {base_ac} + DEX mod capped at {dex_part}")
        elif category == "heavy":
            total_ac = base_ac
            reason_parts.append(f"{armor_name}: {base_ac}")
        else:
            total_ac = base_ac + dex_mod
            reason_parts.append(f"{armor_name}: fallback {base_ac} + DEX mod {dex_mod}")

        armor_bonus, armor_bonus_reasons = get_item_ac_bonus(body_armor)
        total_ac += armor_bonus
        reason_parts.extend(armor_bonus_reasons)

    if shield is not None:
        shield_def = shield.get("definition", {})
        shield_name = shield_def.get("name", "Shield")
        shield_base = safe_int(shield_def.get("armorClass"), 0)
        shield_bonus, shield_bonus_reasons = get_item_ac_bonus(shield)

        total_ac += shield_base + shield_bonus
        reason_parts.append(f"{shield_name}: base shield AC {shield_base}")
        reason_parts.extend(shield_bonus_reasons)

    return total_ac, " + ".join(reason_parts)


def calculate_actual_hit_points(
    data: dict[str, Any],
    final_stats: dict[str, int],
    total_level: int,
    component_name_map: dict[str, str],
) -> tuple[int, str]:
    override_hp = data.get("overrideHitPoints")
    if isinstance(override_hp, int):
        return override_hp, "used overrideHitPoints"

    base_hp = safe_int(data.get("baseHitPoints"))
    bonus_hp = safe_int(data.get("bonusHitPoints"))
    con_mod = ability_mod(final_stats["constitution"])

    if bonus_hp:
        total = base_hp + bonus_hp
        reason_parts = [f"baseHitPoints {base_hp}", f"bonusHitPoints {bonus_hp}"]
    else:
        total = base_hp + (con_mod * total_level)
        reason_parts = [f"baseHitPoints {base_hp}", f"CON mod {con_mod} * level {total_level}"]

    if has_tough_feat(data, component_name_map):
        tough_bonus = 2 * total_level
        total += tough_bonus
        reason_parts.append(f"Tough feat {tough_bonus}")

    return total, " + ".join(reason_parts)


def calculate_passive_perception(
    data: dict[str, Any],
    final_stats: dict[str, int],
    total_level: int,
    modifiers: list[dict[str, Any]],
) -> tuple[int, str]:
    api_pp = data.get("passivePerception")
    if isinstance(api_pp, int) and api_pp > 0:
        return api_pp, "used top-level passivePerception"

    wis_mod = ability_mod(final_stats["wisdom"])
    prof_bonus = get_proficiency_bonus(total_level)
    multiplier = get_skill_multiplier(modifiers, "perception")
    proficiency_part = int(prof_bonus * multiplier)

    reason_parts = [f"10 + WIS mod {wis_mod}"]

    if multiplier == 2.0:
        reason_parts.append(f"expertise ({prof_bonus} * 2)")
    elif multiplier == 1.0:
        reason_parts.append(f"proficiency bonus {prof_bonus}")
    elif multiplier == 0.5:
        reason_parts.append(f"half proficiency {proficiency_part}")

    explicit_bonus = 0
    for mod in modifiers:
        if mod.get("type") == "bonus" and mod.get("subType") == "passive-perception":
            explicit_bonus += safe_int(mod.get("value"), safe_int(mod.get("fixedValue")))

    if explicit_bonus:
        reason_parts.append(f"explicit bonuses {explicit_bonus}")

    total = 10 + wis_mod + proficiency_part + explicit_bonus
    return total, " + ".join(reason_parts)


def extract_stats(
    data: dict[str, Any],
    total_level: int,
    component_name_map: dict[str, str],
    modifiers: list[dict[str, Any]],
) -> dict[str, int]:
    base_stats = get_base_stats(data)
    ability_bonuses, _ = resolve_ability_bonuses(modifiers, component_name_map)
    final_stats = apply_ability_bonuses(base_stats, ability_bonuses)

    active_set_modifiers = get_active_set_stat_modifiers(data)
    final_stats, _ = apply_set_stat_modifiers(final_stats, active_set_modifiers)

    return {
        "strength": final_stats["strength"],
        "dexterity": final_stats["dexterity"],
        "constitution": final_stats["constitution"],
        "intelligence": final_stats["intelligence"],
        "wisdom": final_stats["wisdom"],
        "charisma": final_stats["charisma"],
        "hit_points": calculate_actual_hit_points(data, final_stats, total_level, component_name_map)[0],
        "armor_class": calculate_armor_class(data, final_stats)[0],
        "passive_perception": calculate_passive_perception(data, final_stats, total_level, modifiers)[0],
    }


def extract_classes(data: dict[str, Any]) -> tuple[list[dict[str, Any]], int]:
    classes = []
    total_level = 0

    for c in data.get("classes", []):
        if not isinstance(c, dict):
            continue

        level = safe_int(c.get("level"))
        total_level += level

        subclass_definition = c.get("subclassDefinition", {})
        if not subclass_definition:
            logging.info(f"No subclass found for class '{c['definition']['name']}' in character ID {data.get('id')}")

        subclass_name = subclass_definition.get("name") if subclass_definition else None
        class_description = c.get("definition", {}).get("description", "No description available.")
        subclass_description = subclass_definition.get("description", "No description available.") if subclass_definition else "No description available."

        classes.append({
            "class_name": c["definition"]["name"],
            "subclass_name": subclass_name,
            "level": level,
            "class_description": class_description,
            "subclass_description": subclass_description,
        })

    return classes, total_level


def extract_spell_slots(data: dict[str, Any]) -> dict[str, dict[str, int]]:
    slots = data.get("spellSlots", [])

    return {
        str(slot["level"]): {
            "available": slot["available"],
            "used": slot["used"],
        }
        for slot in slots
    }


def extract_equipment(data: dict[str, Any]) -> list[dict[str, Any]]:
    equipment = []

    for item in data.get("inventory", []):
        definition = item.get("definition", {})
        if not isinstance(definition, dict):
            continue

        equipment.append({
            "item_name": definition.get("name"),
            "type": definition.get("filterType"),
            "rarity": definition.get("rarity"),
            "is_magical": definition.get("magic", False),
            "quantity": item.get("quantity", 1),
            "tags": definition.get("tags", []),
        })

    return equipment


def iter_spell_entries(node: Any):
    """
    Recursively yields spell entry dicts that contain a `definition` dict.
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


def extract_spells(data: dict[str, Any]) -> list[dict[str, Any]]:
    spells_out = []
    seen_spell_keys: set[tuple[str, Any]] = set()

    candidate_roots = []

    if "spells" in data:
        candidate_roots.append(data["spells"])

    if "classSpells" in data:
        candidate_roots.append(data["classSpells"])

    for root in candidate_roots:
        for spell in iter_spell_entries(root):
            definition = spell.get("definition")
            if not isinstance(definition, dict):
                continue

            spell_name = definition.get("name")
            spell_level = definition.get("level")
            dedupe_key = (str(spell_name), spell_level)

            if dedupe_key in seen_spell_keys:
                continue
            seen_spell_keys.add(dedupe_key)

            component_map = {
                1: "Verbal",
                2: "Somatic",
                3: "Material",
            }

            raw_components = definition.get("components", [])
            components = [component_map.get(c, str(c)) for c in raw_components]

            modifiers = definition.get("modifiers") or []
            damage = None
            if modifiers and isinstance(modifiers, list):
                first_modifier = modifiers[0]
                if isinstance(first_modifier, dict):
                    die = first_modifier.get("die")
                    if isinstance(die, dict):
                        damage = die.get("dieString")

            spells_out.append({
                "spell_name": spell_name,
                "description": definition.get("description", ""),
                "level": spell_level,
                "school": definition.get("school"),
                "casting_time": definition.get("castingTimeDescription"),
                "range": definition.get("range"),
                "duration": definition.get("duration"),
                "damage": damage,
                "is_concentration": definition.get("concentration", "Unknown"),
                "is_ritual": definition.get("ritual", "Unknown"),
                "components": ",".join(components),
                "material_components": definition.get("componentsDescription"),
                "consumes_material": "Material" in components,
                "tags": definition.get("tags", []),
            })

    return spells_out


def extract_name(data: dict[str, Any]) -> Optional[str]:
    name = data.get("username")
    if not name:
        logging.warning(f"No player name found for character ID {data.get('id')}")
        return None
    logging.info(f"Extracted player name: {name}")
    return name


def extract_race(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    race = data.get("race", {})
    race_name = race.get("fullName") if race else None
    race_description = race.get("description") if race else None

    if not race:
        logging.warning(f"No race found for character ID {data.get('id')}")
        return None

    logging.info(f"Extracted race: {race_name}")

    return {
        "name": race_name,
        "description": race_description,
    }


def get_dnd_beyond_info(url: str) -> Optional[dict[str, Any]]:
    try:
        logging.info(f"Extracting DND Beyond info from URL: {url}")
        match = re.search(r"/characters/(\d+)", url)
    except Exception as e:
        logging.error(f"Error extracting character ID from URL '{url}': {e}")
        return None

    if not match:
        return None

    character_id = match.group(1)
    response = requests.get(f'{ENV["DND_BEYOND_API"]}{character_id}')

    if response.status_code != 200:
        return None

    data = response.json().get("data", {})
    if not isinstance(data, dict):
        return None

    classes, level = extract_classes(data)
    component_name_map = get_component_name_map(data)
    modifiers = collect_modifiers(data)

    stats = extract_stats(data, level, component_name_map, modifiers)
    spell_slots = extract_spell_slots(data)
    equipment = extract_equipment(data)
    spells = extract_spells(data)
    player_name = extract_name(data)
    race = extract_race(data)

    logging.info(f"Extracted stats for character ID {character_id}: {stats}")
    logging.info(f"Extracted classes for character ID {character_id}: {classes} with total level {level}")

    return {
        "player_name": player_name,
        "dnd_beyond_id": character_id,
        "level": level,
        "stats": stats,
        "classes": classes,
        "spell_slots": spell_slots,
        "equipment": equipment,
        "spells": spells,
        "race": race,
        "gold": data.get("currencies", {}).get("gp", 0),
    }

if __name__ == "__main__":
    pass