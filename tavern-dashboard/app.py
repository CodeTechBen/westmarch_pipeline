from flask import Flask, render_template, jsonify, request
from db import get_connection
from collections import defaultdict

app = Flask(__name__)


CLASS_SUMMARY_CTE = """
class_summary AS (
    SELECT
        cc.character_id,
        STRING_AGG(
            CASE
                WHEN cl.class_name IS NULL THEN 'Unknown'
                WHEN sc.subclass_name IS NOT NULL THEN cl.class_name || ' (' || sc.subclass_name || ')'
                ELSE cl.class_name
            END,
            ', '
            ORDER BY cl.class_name, sc.subclass_name
        ) AS class_display
    FROM character_class cc
    LEFT JOIN class cl
        ON cc.class_id = cl.class_id
    LEFT JOIN subclass sc
        ON cc.subclass_id = sc.subclass_id
    GROUP BY cc.character_id
)
"""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stats")
def stats():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM character;")
    characters = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM player;")
    players = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM class;")
    classes = cur.fetchone()[0]

    cur.close()
    conn.close()

    return jsonify({
        "characters": characters,
        "players": players,
        "classes": classes
    })


@app.route("/api/sessions")
def sessions():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT session_id, session_name
        FROM session
        ORDER BY date DESC
        LIMIT 10;
    """)

    sessions = [
        {"id": row[0], "name": row[1]}
        for row in cur.fetchall()
    ]

    cur.close()
    conn.close()

    return jsonify(sessions)


@app.route("/api/class-distribution")
def class_distribution():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT c.class_name, COUNT(*) AS count
        FROM character_class cc
        JOIN class c ON cc.class_id = c.class_id
        GROUP BY c.class_name
        ORDER BY count DESC;
    """)

    data = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify({
        "labels": [row[0] for row in data],
        "values": [row[1] for row in data]
    })


@app.route("/api/search")
def search():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify([])

    conn = get_connection()
    cur = conn.cursor()

    query = f"%{q}%"
    results = []

    cur.execute("""
        SELECT character_id, character_name
        FROM character
        WHERE character_name ILIKE %s
        LIMIT 5
    """, (query,))
    for row in cur.fetchall():
        results.append({
            "id": row[0],
            "name": row[1],
            "type": "Character",
            "url": f"/character/{row[0]}"
        })

    cur.execute("""
        SELECT player_id, player_name
        FROM player
        WHERE player_name ILIKE %s
           OR discord_name ILIKE %s
           OR dnd_beyond_name ILIKE %s
        LIMIT 5
    """, (query, query, query))
    for row in cur.fetchall():
        results.append({
            "id": row[0],
            "name": row[1],
            "type": "Player",
            "url": f"/player/{row[0]}"
        })

    cur.execute("""
        SELECT spell_id, spell_name
        FROM spell
        WHERE spell_name ILIKE %s
        LIMIT 5
    """, (query,))
    for row in cur.fetchall():
        results.append({
            "id": row[0],
            "name": row[1],
            "type": "Spell",
            "url": f"/spell/{row[0]}"
        })

    cur.execute("""
        SELECT item_id, item_name
        FROM item
        WHERE item_name ILIKE %s
        LIMIT 5
    """, (query,))
    for row in cur.fetchall():
        results.append({
            "id": row[0],
            "name": row[1],
            "type": "Item",
            "url": f"/item/{row[0]}"
        })

    cur.execute("""
        SELECT session_id, session_name
        FROM session
        WHERE session_name ILIKE %s
        LIMIT 5
    """, (query,))
    for row in cur.fetchall():
        results.append({
            "id": row[0],
            "name": row[1],
            "type": "Session",
            "url": f"/session/{row[0]}"
        })

    cur.close()
    conn.close()

    return jsonify(results)


@app.route("/search")
def search_page():
    return render_template("search_results.html")


@app.route("/api/search/full")
def full_search():
    q = request.args.get("q", "").strip()
    filter_type = request.args.get("type", "all").strip().lower()

    if not q:
        return jsonify({
            "query": "",
            "items": [],
            "spells": [],
            "characters": [],
            "available_tags": []
        })

    conn = get_connection()
    cur = conn.cursor()

    query = f"%{q}%"

    items = []
    spells = []
    characters = []
    available_tags = set()

    if filter_type in ("all", "items"):
        cur.execute("""
            SELECT
                i.item_id,
                i.item_name,
                i.rarity,
                COUNT(DISTINCT inv.character_id) AS owned_by_count
            FROM item i
            LEFT JOIN inventory inv
                ON i.item_id = inv.item_id
            LEFT JOIN item_tag it
                ON i.item_id = it.item_id
            LEFT JOIN tag t
                ON it.tag_id = t.tag_id
            WHERE i.item_name ILIKE %s
               OR i.type ILIKE %s
               OR t.tag_name ILIKE %s
            GROUP BY i.item_id, i.item_name, i.rarity
            ORDER BY i.item_name
            LIMIT 50
        """, (query, query, query))

        for row in cur.fetchall():
            items.append({
                "item_id": row[0],
                "item_name": row[1],
                "rarity": row[2],
                "owned_by_count": row[3]
            })

        cur.execute("""
            SELECT DISTINCT t.tag_name
            FROM item i
            JOIN item_tag it
                ON i.item_id = it.item_id
            JOIN tag t
                ON it.tag_id = t.tag_id
            WHERE i.item_name ILIKE %s
               OR i.type ILIKE %s
               OR t.tag_name ILIKE %s
            ORDER BY t.tag_name
            LIMIT 20
        """, (query, query, query))
        available_tags.update(row[0] for row in cur.fetchall())

    if filter_type in ("all", "spells"):
        cur.execute("""
            SELECT
                s.spell_id,
                s.spell_name,
                s.level,
                COUNT(DISTINCT sb.character_id) AS known_by_count
            FROM spell s
            LEFT JOIN spellbook sb
                ON s.spell_id = sb.spell_id
            LEFT JOIN spell_tag st
                ON s.spell_id = st.spell_id
            LEFT JOIN tag t
                ON st.tag_id = t.tag_id
            WHERE s.spell_name ILIKE %s
               OR s.school ILIKE %s
               OR t.tag_name ILIKE %s
            GROUP BY s.spell_id, s.spell_name, s.level
            ORDER BY s.level, s.spell_name
            LIMIT 50
        """, (query, query, query))

        for row in cur.fetchall():
            spells.append({
                "spell_id": row[0],
                "spell_name": row[1],
                "level": row[2],
                "known_by_count": row[3]
            })

        cur.execute("""
            SELECT DISTINCT t.tag_name
            FROM spell s
            JOIN spell_tag st
                ON s.spell_id = st.spell_id
            JOIN tag t
                ON st.tag_id = t.tag_id
            WHERE s.spell_name ILIKE %s
               OR s.school ILIKE %s
               OR t.tag_name ILIKE %s
            ORDER BY t.tag_name
            LIMIT 20
        """, (query, query, query))
        available_tags.update(row[0] for row in cur.fetchall())

    if filter_type in ("all", "characters"):
        cur.execute(f"""
            WITH
            healing_spells AS (
                SELECT DISTINCT sb.character_id, sb.spell_id
                FROM spellbook sb
                JOIN spell_tag st
                    ON sb.spell_id = st.spell_id
                JOIN tag t
                    ON st.tag_id = t.tag_id
                WHERE t.tag_name ILIKE %s
            ),
            healing_items AS (
                SELECT DISTINCT inv.character_id, inv.item_id
                FROM inventory inv
                JOIN item_tag it
                    ON inv.item_id = it.item_id
                JOIN tag t
                    ON it.tag_id = t.tag_id
                WHERE t.tag_name ILIKE %s
            ),
            latest_growth AS (
                SELECT DISTINCT ON (cg.character_id)
                    cg.character_id,
                    cg.level
                FROM character_growth cg
                ORDER BY cg.character_id, cg.time DESC
            ),
            {CLASS_SUMMARY_CTE}
            SELECT
                c.character_id,
                c.character_name,
                p.player_name,
                COALESCE(cs.class_display, 'Unknown') AS class_name,
                COALESCE(lg.level, c.starting_level) AS level,
                COUNT(DISTINCT hs.spell_id) AS healing_spell_count,
                COUNT(DISTINCT hi.item_id) AS healing_item_count
            FROM character c
            JOIN player p
                ON c.player_id = p.player_id
            LEFT JOIN latest_growth lg
                ON c.character_id = lg.character_id
            LEFT JOIN class_summary cs
                ON c.character_id = cs.character_id
            LEFT JOIN healing_spells hs
                ON c.character_id = hs.character_id
            LEFT JOIN healing_items hi
                ON c.character_id = hi.character_id
            WHERE c.character_name ILIKE %s
               OR p.player_name ILIKE %s
               OR COALESCE(cs.class_display, '') ILIKE %s
               OR hs.spell_id IS NOT NULL
               OR hi.item_id IS NOT NULL
            GROUP BY
                c.character_id,
                c.character_name,
                p.player_name,
                cs.class_display,
                lg.level,
                c.starting_level
            ORDER BY c.character_name
            LIMIT 50
        """, (query, query, query, query, query))

        for row in cur.fetchall():
            characters.append({
                "character_id": row[0],
                "character_name": row[1],
                "player_name": row[2],
                "class_display": f"{row[3]} {row[4]}",
                "healing_spell_count": row[5],
                "healing_item_count": row[6]
            })

    cur.close()
    conn.close()

    return jsonify({
        "query": q,
        "items": items,
        "spells": spells,
        "characters": characters,
        "available_tags": sorted(available_tags)
    })


@app.route("/api/sessions/list")
def session_list():
    conn = get_connection()
    cur = conn.cursor()

    offset = request.args.get("offset", 0, type=int)
    limit = request.args.get("limit", 10, type=int)
    dm = request.args.get("dm")

    query = """
        SELECT session_id, session_name, date, dm_name, player_count, tier
        FROM session_summary
    """
    params = []

    if dm:
        query += " WHERE dm_name = %s"
        params.append(dm)

    query += " ORDER BY date DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    cur.execute(query, params)
    rows = cur.fetchall()

    cur.close()
    conn.close()

    return jsonify([
        {
            "id": r[0],
            "name": r[1],
            "date": r[2].strftime("%Y-%m-%d"),
            "dm": r[3],
            "players": r[4],
            "tier": f"Tier {r[5]}" if r[5] else "Unknown"
        }
        for r in rows
    ])


@app.route("/api/dms")
def get_dms():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT p.player_name
        FROM session s
        JOIN player p ON s.dm_player_id = p.player_id
    """)

    dms = [row[0] for row in cur.fetchall()]

    cur.close()
    conn.close()

    return jsonify(dms)


@app.route("/sessions")
def sessions_page():
    return render_template("sessions.html")


@app.route("/api/session/<int:session_id>")
def session_detail_api(session_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT s.session_id, s.session_name, s.date, p.player_name, p.player_id
        FROM session s
        LEFT JOIN player p ON s.dm_player_id = p.player_id
        WHERE s.session_id = %s
    """, (session_id,))
    session = cur.fetchone()

    if not session:
        cur.close()
        conn.close()
        return jsonify({"error": "Session not found"}), 404

    cur.execute(f"""
        WITH {CLASS_SUMMARY_CTE}
        SELECT
            c.character_id,
            c.character_name,
            c.picture_url,
            p.player_name,
            p.player_id,
            COALESCE(cs.class_display, 'Unknown') AS class_display,
            cg.level,
            cg.hit_points,
            cg.armor_class,
            cg.passive_perception,
            cg.strength,
            cg.dexterity,
            cg.constitution,
            cg.intelligence,
            cg.wisdom,
            cg.charisma,
            cg.gold
        FROM character_growth cg
        JOIN character c ON cg.character_id = c.character_id
        JOIN player p ON c.player_id = p.player_id
        LEFT JOIN class_summary cs ON c.character_id = cs.character_id
        WHERE cg.session_id = %s
        ORDER BY c.character_name
    """, (session_id,))
    characters = cur.fetchall()

    tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}

    for c in characters:
        level = c[6]
        if level is None:
            continue
        if 0 <= level <= 4:
            tier_counts[1] += 1
        elif 5 <= level <= 10:
            tier_counts[2] += 1
        elif 11 <= level <= 15:
            tier_counts[3] += 1
        else:
            tier_counts[4] += 1

    tier = max(tier_counts, key=tier_counts.get) if characters else None

    tier_label_map = {
        1: "Tier 1 (Levels 0–4)",
        2: "Tier 2 (Levels 5–10)",
        3: "Tier 3 (Levels 11–15)",
        4: "Tier 4 (Levels 16+)"
    }

    cur.execute("""
        SELECT
            c.character_name,
            i.rarity,
            COUNT(*) AS item_count
        FROM inventory inv
        JOIN character c
            ON inv.character_id = c.character_id
        JOIN item i
            ON inv.item_id = i.item_id
        WHERE inv.growth_id IN (
            SELECT growth_id
            FROM character_growth
            WHERE session_id = %s
        )
        GROUP BY c.character_name, i.rarity
    """, (session_id,))
    items = cur.fetchall()

    cur.close()
    conn.close()

    char_data = []
    for c in characters:
        char_data.append({
            "id": c[0],
            "name": c[1],
            "avatar": c[2],
            "player": c[3],
            "player_id": c[4],
            "class_display": c[5],
            "level": c[6],
            "hp": c[7],
            "ac": c[8],
            "pp": c[9],
            "stats": {
                "STR": c[10],
                "DEX": c[11],
                "CON": c[12],
                "INT": c[13],
                "WIS": c[14],
                "CHA": c[15]
            },
            "gold": c[16]
        })

    item_map = {}

    for char in char_data:
        item_map[char["name"]] = {
            "gold": char["gold"],
            "Common": 0,
            "Uncommon": 0,
            "Rare": 0,
            "Very Rare": 0,
            "Legendary": 0
        }

    for name, rarity, count in items:
        if name not in item_map:
            item_map[name] = {
                "gold": 0,
                "Common": 0,
                "Uncommon": 0,
                "Rare": 0,
                "Very Rare": 0,
                "Legendary": 0
            }
        item_map[name][rarity] = count

    totals = {
        name: data["Common"] + data["Uncommon"] + data["Rare"] + data["Very Rare"] + data["Legendary"]
        for name, data in item_map.items()
    }

    recommendation = min(totals, key=totals.get) if totals else None

    return jsonify({
        "session": {
            "id": session[0],
            "name": session[1],
            "date": session[2].strftime("%B %d, %Y"),
            "dm": session[3],
            "tier": tier_label_map.get(tier, "Tier Unknown")
        },
        "characters": char_data,
        "items": item_map,
        "recommendation": recommendation
    })


@app.route("/api/spell/<int:spell_id>")
def spell_detail_api(spell_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            spell_id,
            spell_name,
            description,
            level,
            school,
            casting_time,
            range,
            consumes_material,
            material_components,
            duration,
            is_concentration,
            is_ritual
        FROM spell
        WHERE spell_id = %s
    """, (spell_id,))
    spell = cur.fetchone()

    if not spell:
        cur.close()
        conn.close()
        return jsonify({"error": "Spell not found"}), 404

    cur.execute("""
        SELECT t.tag_name
        FROM spell_tag st
        JOIN tag t
            ON st.tag_id = t.tag_id
        WHERE st.spell_id = %s
        ORDER BY t.tag_name
    """, (spell_id,))
    tags = [row[0] for row in cur.fetchall()]

    cur.execute(f"""
        WITH
        latest_growth AS (
            SELECT DISTINCT ON (cg.character_id)
                cg.character_id,
                cg.level
            FROM character_growth cg
            ORDER BY cg.character_id, cg.time DESC
        ),
        {CLASS_SUMMARY_CTE}
        SELECT DISTINCT
            c.character_id,
            c.character_name,
            p.player_id,
            p.player_name,
            COALESCE(cs.class_display, 'Unknown') AS class_display,
            COALESCE(cg_spell.level, lg.level, c.starting_level) AS character_level,
            c.is_active
        FROM spellbook sb
        JOIN character c
            ON sb.character_id = c.character_id
        JOIN player p
            ON c.player_id = p.player_id
        LEFT JOIN character_growth cg_spell
            ON sb.growth_id = cg_spell.growth_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN class_summary cs
            ON c.character_id = cs.character_id
        WHERE sb.spell_id = %s
        ORDER BY c.is_active DESC, c.character_name
    """, (spell_id,))
    known_by_rows = cur.fetchall()

    cur.close()
    conn.close()

    components = ["V", "S"]
    if spell[7]:
        if spell[8]:
            components.append(f"M ({spell[8]})")
        else:
            components.append("M")

    known_by = []
    for row in known_by_rows:
        known_by.append({
            "character_id": row[0],
            "character_name": row[1],
            "player_id": row[2],
            "player_name": row[3],
            "class_display": row[4],
            "level": row[5],
            "is_active": row[6]
        })

    return jsonify({
        "spell": {
            "id": spell[0],
            "name": spell[1],
            "description": spell[2],
            "level": spell[3],
            "school": spell[4],
            "casting_time": spell[5],
            "range": spell[6],
            "components": ", ".join(components),
            "duration": spell[9],
            "is_concentration": spell[10],
            "is_ritual": spell[11]
        },
        "tags": tags,
        "known_by": known_by
    })


@app.route("/spell/<int:spell_id>")
def spell_detail_page(spell_id):
    return render_template("spell_detail.html", spell_id=spell_id)


@app.route("/session/<int:session_id>")
def session_detail_page(session_id):
    return render_template("session_detail.html", session_id=session_id)


@app.route("/player/<int:player_id>")
def player_detail_page(player_id):
    return render_template("player_detail.html", player_id=player_id)


@app.route("/api/player/<int:player_id>")
def player_detail_api(player_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            player_id,
            player_name,
            discord_name,
            dnd_beyond_name,
            join_date
        FROM player
        WHERE player_id = %s
    """, (player_id,))
    player = cur.fetchone()

    if not player:
        cur.close()
        conn.close()
        return jsonify({"error": "Player not found"}), 404

    cur.execute("""
        SELECT COUNT(DISTINCT cg.session_id)
        FROM character_growth cg
        JOIN character c
            ON cg.character_id = c.character_id
        WHERE c.player_id = %s
          AND cg.session_id IS NOT NULL
    """, (player_id,))
    sessions_played = cur.fetchone()[0]

    cur.execute(f"""
        WITH
        latest_growth AS (
            SELECT DISTINCT ON (cg.character_id)
                cg.character_id,
                cg.level,
                cg.hit_points,
                cg.gold,
                cg.time
            FROM character_growth cg
            ORDER BY cg.character_id, cg.time DESC
        ),
        session_counts AS (
            SELECT
                cg.character_id,
                COUNT(*) AS session_count
            FROM character_growth cg
            WHERE cg.session_id IS NOT NULL
            GROUP BY cg.character_id
        ),
        {CLASS_SUMMARY_CTE}
        SELECT
            c.character_id,
            c.character_name,
            c.picture_url,
            c.is_active,
            r.race_name,
            COALESCE(cs.class_display, 'Unknown') AS class_display,
            lg.level,
            lg.hit_points,
            lg.gold,
            COALESCE(scnt.session_count, 0) AS session_count
        FROM character c
        JOIN race r
            ON c.race_id = r.race_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN session_counts scnt
            ON c.character_id = scnt.character_id
        LEFT JOIN class_summary cs
            ON c.character_id = cs.character_id
        WHERE c.player_id = %s
        ORDER BY c.is_active DESC, c.character_name
    """, (player_id,))
    characters = cur.fetchall()

    cur.execute("""
        SELECT
            TO_CHAR(DATE_TRUNC('month', s.date), 'YYYY-MM') AS month_key,
            COUNT(*) AS session_count
        FROM character_growth cg
        JOIN character c
            ON cg.character_id = c.character_id
        JOIN session s
            ON cg.session_id = s.session_id
        WHERE c.player_id = %s
        GROUP BY DATE_TRUNC('month', s.date)
        ORDER BY DATE_TRUNC('month', s.date)
    """, (player_id,))
    sessions_per_month = cur.fetchall()

    cur.execute("""
        SELECT
            s.session_id,
            s.session_name,
            s.date,
            ch.character_id,
            ch.character_name,
            dm.player_name AS dm_name
        FROM character_growth cg
        JOIN character ch
            ON cg.character_id = ch.character_id
        JOIN session s
            ON cg.session_id = s.session_id
        LEFT JOIN player dm
            ON s.dm_player_id = dm.player_id
        WHERE ch.player_id = %s
        ORDER BY s.date DESC, s.session_id DESC
        LIMIT 10
    """, (player_id,))
    recent_sessions = cur.fetchall()

    cur.close()
    conn.close()

    character_data = []
    for row in characters:
        character_id = row[0]
        character_name = row[1]
        picture_url = row[2]
        is_active = row[3]
        race_name = row[4]
        class_display = row[5]
        level = row[6]
        hit_points = row[7]
        gold = row[8]
        session_count = row[9]

        tier = "Unknown"
        if level is not None:
            if 0 <= level <= 4:
                tier = "Tier 1"
            elif 5 <= level <= 10:
                tier = "Tier 2"
            elif 11 <= level <= 15:
                tier = "Tier 3"
            else:
                tier = "Tier 4"

        subtitle = f"{race_name} {class_display or 'Unknown Class'}"
        if level is not None:
            subtitle += f" {level}"

        character_data.append({
            "id": character_id,
            "name": character_name,
            "avatar": picture_url,
            "is_active": is_active,
            "status": "ACTIVE" if is_active else "RETIRED",
            "subtitle": subtitle,
            "tier": tier,
            "sessions": session_count,
            "hp": hit_points,
            "gold": gold
        })

    chart_labels = [row[0] for row in sessions_per_month]
    chart_values = [row[1] for row in sessions_per_month]

    recent_session_data = []
    for row in recent_sessions:
        recent_session_data.append({
            "session_id": row[0],
            "session_name": row[1],
            "date": row[2].strftime("%b %d, %Y"),
            "character_id": row[3],
            "character_name": row[4],
            "dm_name": row[5] or "Unknown"
        })

    return jsonify({
        "player": {
            "id": player[0],
            "name": player[1],
            "discord_name": player[2],
            "dnd_beyond_name": player[3],
            "join_date": player[4].strftime("%B %d, %Y"),
            "sessions_played": sessions_played
        },
        "characters": character_data,
        "activity": {
            "labels": chart_labels,
            "values": chart_values
        },
        "recent_sessions": recent_session_data
    })


@app.route("/character/<int:character_id>")
def character_detail_page(character_id):
    return render_template("character_detail.html", character_id=character_id)


@app.route("/api/character/<int:character_id>")
def character_detail_api(character_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(f"""
        WITH
        latest_growth AS (
            SELECT DISTINCT ON (cg.character_id)
                cg.character_id,
                cg.level,
                cg.strength,
                cg.dexterity,
                cg.constitution,
                cg.intelligence,
                cg.wisdom,
                cg.charisma,
                cg.hit_points,
                cg.gold,
                cg.passive_perception,
                cg.armor_class,
                cg.time
            FROM character_growth cg
            WHERE cg.character_id = %s
            ORDER BY cg.character_id, cg.time DESC
        ),
        session_count AS (
            SELECT
                cg.character_id,
                COUNT(*) AS sessions_played
            FROM character_growth cg
            WHERE cg.character_id = %s
              AND cg.session_id IS NOT NULL
            GROUP BY cg.character_id
        ),
        {CLASS_SUMMARY_CTE}
        SELECT
            c.character_id,
            c.character_name,
            c.picture_url,
            c.dnd_beyond_id,
            c.is_active,
            p.player_id,
            p.player_name,
            r.race_name,
            COALESCE(cs.class_display, 'Unknown') AS class_display,
            lg.level,
            lg.strength,
            lg.dexterity,
            lg.constitution,
            lg.intelligence,
            lg.wisdom,
            lg.charisma,
            lg.hit_points,
            lg.gold,
            lg.passive_perception,
            lg.armor_class,
            COALESCE(scnt.sessions_played, 0) AS sessions_played
        FROM character c
        JOIN player p
            ON c.player_id = p.player_id
        JOIN race r
            ON c.race_id = r.race_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN session_count scnt
            ON c.character_id = scnt.character_id
        LEFT JOIN class_summary cs
            ON c.character_id = cs.character_id
        WHERE c.character_id = %s
    """, (character_id, character_id, character_id))
    character = cur.fetchone()

    if not character:
        cur.close()
        conn.close()
        return jsonify({"error": "Character not found"}), 404

    cur.execute("""
        SELECT
            COALESCE(s.session_name, CONCAT('Snapshot ', cg.growth_id)) AS label,
            cg.level,
            cg.hit_points,
            cg.gold
        FROM character_growth cg
        LEFT JOIN session s
            ON cg.session_id = s.session_id
        WHERE cg.character_id = %s
        ORDER BY cg.time
    """, (character_id,))
    growth_rows = cur.fetchall()

    cur.execute("""
        WITH latest_growth AS (
            SELECT cg.growth_id
            FROM character_growth cg
            WHERE cg.character_id = %s
            ORDER BY cg.time DESC
            LIMIT 1
        )
        SELECT
            i.item_id,
            i.item_name,
            i.rarity,
            inv.quantity
        FROM inventory inv
        JOIN item i
            ON inv.item_id = i.item_id
        WHERE inv.character_id = %s
          AND (
              inv.growth_id = (SELECT growth_id FROM latest_growth)
              OR inv.growth_id IS NULL
          )
        ORDER BY i.rarity, i.item_name
    """, (character_id, character_id))
    inventory_rows = cur.fetchall()

    cur.execute("""
        WITH latest_growth AS (
            SELECT cg.growth_id
            FROM character_growth cg
            WHERE cg.character_id = %s
            ORDER BY cg.time DESC
            LIMIT 1
        )
        SELECT DISTINCT
            sp.spell_id,
            sp.spell_name,
            sp.level,
            sp.school
        FROM spellbook sb
        JOIN spell sp
            ON sb.spell_id = sp.spell_id
        WHERE sb.character_id = %s
          AND (
              sb.growth_id = (SELECT growth_id FROM latest_growth)
              OR sb.growth_id IS NULL
          )
        ORDER BY sp.level, sp.spell_name
    """, (character_id, character_id))
    spell_rows = cur.fetchall()

    cur.execute("""
        WITH growth_with_prev AS (
            SELECT
                cg.growth_id,
                cg.character_id,
                cg.session_id,
                cg.level,
                cg.gold,
                LAG(cg.level) OVER (PARTITION BY cg.character_id ORDER BY cg.time) AS prev_level,
                LAG(cg.gold) OVER (PARTITION BY cg.character_id ORDER BY cg.time) AS prev_gold
            FROM character_growth cg
            WHERE cg.character_id = %s
        )
        SELECT
            s.session_id,
            s.session_name,
            s.date,
            dm.player_name AS dm_name,
            gwp.prev_level,
            gwp.level,
            gwp.prev_gold,
            gwp.gold
        FROM growth_with_prev gwp
        JOIN session s
            ON gwp.session_id = s.session_id
        LEFT JOIN player dm
            ON s.dm_player_id = dm.player_id
        WHERE gwp.session_id IS NOT NULL
        ORDER BY s.date DESC, s.session_id DESC
    """, (character_id,))
    session_rows = cur.fetchall()

    cur.close()
    conn.close()

    level = character[9]
    if level is None:
        tier = "Unknown"
    elif 0 <= level <= 4:
        tier = "Tier 1"
    elif 5 <= level <= 10:
        tier = "Tier 2"
    elif 11 <= level <= 15:
        tier = "Tier 3"
    else:
        tier = "Tier 4"

    dnd_beyond_url = None
    if character[3]:
        dnd_beyond_url = f"https://www.dndbeyond.com/characters/{character[3]}"

    growth_labels = [row[0] for row in growth_rows]
    growth_levels = [row[1] for row in growth_rows]
    growth_hp = [row[2] for row in growth_rows]
    growth_gold = [row[3] for row in growth_rows]

    inventory = [
        {
            "item_id": row[0],
            "item_name": row[1],
            "rarity": row[2],
            "quantity": row[3]
        }
        for row in inventory_rows
    ]

    spells = [
        {
            "spell_id": row[0],
            "spell_name": row[1],
            "level": row[2],
            "school": row[3]
        }
        for row in spell_rows
    ]

    session_history = []
    for row in session_rows:
        gold_change = None
        if row[6] is not None and row[7] is not None:
            gold_change = row[7] - row[6]

        session_history.append({
            "session_id": row[0],
            "session_name": row[1],
            "date": row[2].strftime("%b %d"),
            "dm_name": row[3] or "Unknown",
            "level_before": row[4],
            "level_after": row[5],
            "gold_change": gold_change
        })

    return jsonify({
        "character": {
            "id": character[0],
            "name": character[1],
            "avatar": character[2],
            "dnd_beyond_id": character[3],
            "dnd_beyond_url": dnd_beyond_url,
            "is_active": character[4],
            "player_id": character[5],
            "player_name": character[6],
            "race_name": character[7],
            "class_name": character[8],
            "level": character[9],
            "strength": character[10],
            "dexterity": character[11],
            "constitution": character[12],
            "intelligence": character[13],
            "wisdom": character[14],
            "charisma": character[15],
            "hit_points": character[16],
            "gold": character[17],
            "passive_perception": character[18],
            "armor_class": character[19],
            "sessions_played": character[20],
            "tier": tier
        },
        "growth": {
            "labels": growth_labels,
            "level": growth_levels,
            "hp": growth_hp,
            "gold": growth_gold
        },
        "inventory": inventory,
        "spells": spells,
        "session_history": session_history
    })


@app.route("/item/<int:item_id>")
def item_detail_page(item_id):
    return render_template("item_detail.html", item_id=item_id)


@app.route("/api/item/<int:item_id>")
def item_detail_api(item_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            item_id,
            item_name,
            type,
            rarity,
            is_magical
        FROM item
        WHERE item_id = %s
    """, (item_id,))
    item_row = cur.fetchone()

    if not item_row:
        cur.close()
        conn.close()
        return jsonify({"error": "Item not found"}), 404

    cur.execute("""
        SELECT t.tag_name
        FROM item_tag it
        JOIN tag t
            ON it.tag_id = t.tag_id
        WHERE it.item_id = %s
        ORDER BY t.tag_name
    """, (item_id,))
    tags = [row[0] for row in cur.fetchall()]

    cur.execute(f"""
        WITH
        latest_growth AS (
            SELECT DISTINCT ON (cg.character_id)
                cg.character_id,
                cg.level,
                cg.time
            FROM character_growth cg
            ORDER BY cg.character_id, cg.time DESC
        ),
        {CLASS_SUMMARY_CTE}
        SELECT
            c.character_id,
            c.character_name,
            p.player_id,
            p.player_name,
            COALESCE(cs.class_display, 'Unknown') AS class_display,
            COALESCE(SUM(inv.quantity), 0) AS qty,
            c.is_active
        FROM inventory inv
        JOIN character c
            ON inv.character_id = c.character_id
        JOIN player p
            ON c.player_id = p.player_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN class_summary cs
            ON c.character_id = cs.character_id
        WHERE inv.item_id = %s
        GROUP BY
            c.character_id,
            c.character_name,
            p.player_id,
            p.player_name,
            cs.class_display,
            c.is_active
        ORDER BY c.is_active DESC, c.character_name
    """, (item_id,))
    owner_rows = cur.fetchall()

    cur.execute("""
        SELECT
            rarity,
            COUNT(*) AS rarity_count
        FROM item
        GROUP BY rarity
        ORDER BY rarity
    """)
    rarity_rows = cur.fetchall()

    cur.close()
    conn.close()

    owners = []
    for row in owner_rows:
        owners.append({
            "character_id": row[0],
            "character_name": row[1],
            "player_id": row[2],
            "player_name": row[3],
            "class_display": row[4],
            "quantity": row[5],
            "is_active": row[6]
        })

    rarity_labels = [row[0] for row in rarity_rows]
    rarity_values = [row[1] for row in rarity_rows]

    # Placeholder description
    item_description = (
        f"{item_row[1]} is a {item_row[3].lower()} item in the {item_row[2]} category."
        + (" It is magical." if item_row[4] else "")
    )

    return jsonify({
        "item": {
            "id": item_row[0],
            "name": item_row[1],
            "type": item_row[2],
            "rarity": item_row[3],
            "is_magical": item_row[4],
            "description": item_description
        },
        "tags": tags,
        "owners": owners,
        "rarity_distribution": {
            "labels": rarity_labels,
            "values": rarity_values
        }
    })

@app.route("/item-distribution")
def item_distribution_page():
    return render_template("item_distribution.html")


@app.route("/api/item-distribution")
def item_distribution_api():
    tier = request.args.get("tier", "all").strip().lower()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()
    rank_by = request.args.get("rank_by", "character").strip().lower()
    value_mode = request.args.get("value", "gold").strip().lower()

    if rank_by not in ("character", "player"):
        rank_by = "character"

    if value_mode not in ("gold", "items", "both"):
        value_mode = "gold"

    conn = get_connection()
    cur = conn.cursor()

    filters = []
    params = []

    if date_from:
        filters.append("s.date >= %s")
        params.append(date_from)

    if date_to:
        filters.append("s.date <= %s")
        params.append(date_to)

    date_filter_sql = ""
    if filters:
        date_filter_sql = "AND " + " AND ".join(filters)

    if rank_by == "character":
        cur.execute(f"""
            WITH latest_growth AS (
                SELECT DISTINCT ON (cg.character_id)
                    cg.character_id,
                    cg.level,
                    cg.gold,
                    cg.time
                FROM character_growth cg
                JOIN session s
                    ON cg.session_id = s.session_id
                WHERE 1=1
                {date_filter_sql}
                ORDER BY cg.character_id, cg.time DESC
            ),
            item_summary AS (
                SELECT
                    inv.character_id,
                    COUNT(*) AS item_count,
                    MAX(
                        CASE i.rarity
                            WHEN 'Common' THEN 1
                            WHEN 'Uncommon' THEN 2
                            WHEN 'Rare' THEN 3
                            WHEN 'Very Rare' THEN 4
                            WHEN 'Legendary' THEN 5
                            WHEN 'Artifact' THEN 6
                            ELSE 0
                        END
                    ) AS highest_rarity_rank,
                    AVG(
                        CASE i.rarity
                            WHEN 'Common' THEN 10
                            WHEN 'Uncommon' THEN 25
                            WHEN 'Rare' THEN 60
                            WHEN 'Very Rare' THEN 120
                            WHEN 'Legendary' THEN 250
                            WHEN 'Artifact' THEN 500
                            ELSE 0
                        END
                    ) AS avg_rarity_value,
                    SUM(
                        CASE i.rarity
                            WHEN 'Common' THEN 10
                            WHEN 'Uncommon' THEN 25
                            WHEN 'Rare' THEN 60
                            WHEN 'Very Rare' THEN 120
                            WHEN 'Legendary' THEN 250
                            WHEN 'Artifact' THEN 500
                            ELSE 0
                        END * inv.quantity
                    ) AS weighted_item_value
                FROM inventory inv
                JOIN item i
                    ON inv.item_id = i.item_id
                GROUP BY inv.character_id
            )
            SELECT
                c.character_id,
                c.character_name,
                COALESCE(lg.level, c.starting_level) AS level,
                CASE
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 0 AND 4 THEN 1
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 5 AND 10 THEN 2
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 11 AND 15 THEN 3
                    ELSE 4
                END AS tier,
                COALESCE(lg.gold, 0) AS gold,
                COALESCE(isum.item_count, 0) AS item_count,
                COALESCE(isum.avg_rarity_value, 0) AS avg_rarity_value,
                COALESCE(isum.weighted_item_value, 0) AS weighted_item_value,
                COALESCE(lg.gold, 0) + COALESCE(isum.weighted_item_value, 0) AS both_score,
                COALESCE(isum.highest_rarity_rank, 0) AS highest_rarity_rank
            FROM character c
            LEFT JOIN latest_growth lg
                ON c.character_id = lg.character_id
            LEFT JOIN item_summary isum
                ON c.character_id = isum.character_id
            WHERE 1=1
        """, params)

        rows = cur.fetchall()

        ranked_rows = []
        for row in rows:
            tier_value = row[3]
            if tier != "all" and str(tier_value) != tier:
                continue

            ranked_rows.append({
                "id": row[0],
                "name": row[1],
                "level": row[2],
                "tier": tier_value,
                "gold": row[4],
                "item_count": row[5],
                "avg_rarity": map_avg_rarity(row[6]),
                "weighted_item_value": float(row[7] or 0),
                "both_score": float(row[8] or 0),
                "highest_rarity": map_highest_rarity(row[9])
            })

    else:
        cur.execute(f"""
            WITH latest_growth AS (
                SELECT DISTINCT ON (cg.character_id)
                    cg.character_id,
                    cg.level,
                    cg.gold,
                    cg.time
                FROM character_growth cg
                JOIN session s
                    ON cg.session_id = s.session_id
                WHERE 1=1
                {date_filter_sql}
                ORDER BY cg.character_id, cg.time DESC
            ),
            item_summary AS (
                SELECT
                    inv.character_id,
                    COUNT(*) AS item_count,
                    MAX(
                        CASE i.rarity
                            WHEN 'Common' THEN 1
                            WHEN 'Uncommon' THEN 2
                            WHEN 'Rare' THEN 3
                            WHEN 'Very Rare' THEN 4
                            WHEN 'Legendary' THEN 5
                            WHEN 'Artifact' THEN 6
                            ELSE 0
                        END
                    ) AS highest_rarity_rank,
                    AVG(
                        CASE i.rarity
                            WHEN 'Common' THEN 10
                            WHEN 'Uncommon' THEN 25
                            WHEN 'Rare' THEN 60
                            WHEN 'Very Rare' THEN 120
                            WHEN 'Legendary' THEN 250
                            WHEN 'Artifact' THEN 500
                            ELSE 0
                        END
                    ) AS avg_rarity_value,
                    SUM(
                        CASE i.rarity
                            WHEN 'Common' THEN 10
                            WHEN 'Uncommon' THEN 25
                            WHEN 'Rare' THEN 60
                            WHEN 'Very Rare' THEN 120
                            WHEN 'Legendary' THEN 250
                            WHEN 'Artifact' THEN 500
                            ELSE 0
                        END * inv.quantity
                    ) AS weighted_item_value
                FROM inventory inv
                JOIN item i
                    ON inv.item_id = i.item_id
                GROUP BY inv.character_id
            ),
            character_rollup AS (
                SELECT
                    p.player_id,
                    p.player_name,
                    CASE
                        WHEN COALESCE(lg.level, c.starting_level) BETWEEN 0 AND 4 THEN 1
                        WHEN COALESCE(lg.level, c.starting_level) BETWEEN 5 AND 10 THEN 2
                        WHEN COALESCE(lg.level, c.starting_level) BETWEEN 11 AND 15 THEN 3
                        ELSE 4
                    END AS tier,
                    COALESCE(lg.gold, 0) AS gold,
                    COALESCE(isum.item_count, 0) AS item_count,
                    COALESCE(isum.avg_rarity_value, 0) AS avg_rarity_value,
                    COALESCE(isum.weighted_item_value, 0) AS weighted_item_value,
                    COALESCE(isum.highest_rarity_rank, 0) AS highest_rarity_rank
                FROM character c
                JOIN player p
                    ON c.player_id = p.player_id
                LEFT JOIN latest_growth lg
                    ON c.character_id = lg.character_id
                LEFT JOIN item_summary isum
                    ON c.character_id = isum.character_id
            )
            SELECT
                player_id,
                player_name,
                MAX(tier) AS tier,
                SUM(gold) AS gold,
                SUM(item_count) AS item_count,
                AVG(avg_rarity_value) AS avg_rarity_value,
                SUM(weighted_item_value) AS weighted_item_value,
                SUM(gold) + SUM(weighted_item_value) AS both_score,
                MAX(highest_rarity_rank) AS highest_rarity_rank
            FROM character_rollup
            GROUP BY player_id, player_name
        """, params)

        rows = cur.fetchall()

        ranked_rows = []
        for row in rows:
            tier_value = row[2]
            if tier != "all" and str(tier_value) != tier:
                continue

            ranked_rows.append({
                "id": row[0],
                "name": row[1],
                "tier": tier_value,
                "gold": row[3],
                "item_count": row[4],
                "avg_rarity": map_avg_rarity(row[5]),
                "weighted_item_value": float(row[6] or 0),
                "both_score": float(row[7] or 0),
                "highest_rarity": map_highest_rarity(row[8])
            })

    if value_mode == "gold":
        ranked_rows.sort(key=lambda x: x["gold"], reverse=True)
    elif value_mode == "items":
        ranked_rows.sort(key=lambda x: x["weighted_item_value"], reverse=True)
    else:
        ranked_rows.sort(key=lambda x: x["both_score"], reverse=True)

    for i, row in enumerate(ranked_rows, start=1):
        row["rank"] = i

    if value_mode == "gold":
        chart_values = [row["gold"] for row in ranked_rows[:15]]
        chart_title = "Richest to Poorest — Gold"
    elif value_mode == "items":
        chart_values = [row["weighted_item_value"] for row in ranked_rows[:15]]
        chart_title = "Richest to Poorest — Item Value"
    else:
        chart_values = [row["both_score"] for row in ranked_rows[:15]]
        chart_title = "Richest to Poorest — Combined Wealth"

    chart_labels = [
        f'{row["name"]} (Tier {row["tier"]})'
        for row in ranked_rows[:15]
    ]

    cur.execute("""
        SELECT
            i.type,
            COUNT(*) AS type_count
        FROM item i
        GROUP BY i.type
        ORDER BY type_count DESC, i.type
    """)
    type_rows = cur.fetchall()

    item_type_distribution = {
        "labels": [row[0] for row in type_rows],
        "values": [row[1] for row in type_rows]
    }

    cur.execute("""
        SELECT
            i.rarity,
            COUNT(*) AS rarity_count
        FROM item i
        GROUP BY i.rarity
        ORDER BY
            CASE i.rarity
                WHEN 'Common' THEN 1
                WHEN 'Uncommon' THEN 2
                WHEN 'Rare' THEN 3
                WHEN 'Very Rare' THEN 4
                WHEN 'Legendary' THEN 5
                WHEN 'Artifact' THEN 6
                ELSE 99
            END
    """)
    rarity_rows = cur.fetchall()

    item_rarity_distribution = {
        "labels": [row[0] for row in rarity_rows],
        "values": [row[1] for row in rarity_rows]
    }

    cur.close()
    conn.close()

    return jsonify({
        "filters": {
            "tier": tier,
            "date_from": date_from,
            "date_to": date_to,
            "rank_by": rank_by,
            "value": value_mode
        },
        "table": ranked_rows,
        "chart": {
            "title": chart_title,
            "labels": chart_labels,
            "values": chart_values
        },
        "item_type_distribution": item_type_distribution,
        "item_rarity_distribution": item_rarity_distribution
    })


def map_avg_rarity(value):
    if value is None:
        return "None"
    if value < 20:
        return "Common"
    if value < 45:
        return "Uncommon"
    if value < 90:
        return "Rare"
    if value < 180:
        return "Very Rare"
    if value < 400:
        return "Legendary"
    return "Artifact"


def map_highest_rarity(rank):
    mapping = {
        1: "Common",
        2: "Uncommon",
        3: "Rare",
        4: "Very Rare",
        5: "Legendary",
        6: "Artifact"
    }
    return mapping.get(rank, "None")

@app.route("/class-stats")
def class_stats_page():
    return render_template("class_stats.html")


@app.route("/api/class-stats")
def class_stats_api():
    tier = request.args.get("tier", "all").strip().lower()
    active_only = request.args.get("active_only", "true").lower() == "true"

    conn = get_connection()
    cur = conn.cursor()

    filters = []
    params = []

    if active_only:
        filters.append("c.is_active = TRUE")

    if tier != "all":
        filters.append("""
            (
                CASE
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 0 AND 4 THEN 1
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 5 AND 10 THEN 2
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 11 AND 15 THEN 3
                    ELSE 4
                END
            ) = %s
        """)
        params.append(int(tier))

    where_sql = ""
    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    cur.execute(f"""
        WITH latest_growth AS (
            SELECT DISTINCT ON (cg.character_id)
                cg.character_id,
                cg.level
            FROM character_growth cg
            ORDER BY cg.character_id, cg.time DESC
        )
        SELECT
            cl.class_id,
            cl.class_name,
            COUNT(DISTINCT c.character_id) AS class_count
        FROM character c
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        JOIN character_class cc
            ON c.character_id = cc.character_id
        JOIN class cl
            ON cc.class_id = cl.class_id
        {where_sql}
        GROUP BY cl.class_id, cl.class_name
        ORDER BY class_count DESC, cl.class_name
    """, params)

    class_rows = cur.fetchall()

    classes = [
        {
            "class_id": row[0],
            "class_name": row[1],
            "count": row[2]
        }
        for row in class_rows
    ]

    cur.execute(f"""
        WITH latest_growth AS (
            SELECT DISTINCT ON (cg.character_id)
                cg.character_id,
                cg.level
            FROM character_growth cg
            ORDER BY cg.character_id, cg.time DESC
        )
        SELECT
            cl.class_id,
            cl.class_name,
            COALESCE(sc.subclass_name, 'No Subclass') AS subclass_name,
            COUNT(DISTINCT c.character_id) AS subclass_count
        FROM character c
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        JOIN character_class cc
            ON c.character_id = cc.character_id
        JOIN class cl
            ON cc.class_id = cl.class_id
        LEFT JOIN subclass sc
            ON cc.subclass_id = sc.subclass_id
        {where_sql}
        GROUP BY cl.class_id, cl.class_name, COALESCE(sc.subclass_name, 'No Subclass')
        ORDER BY cl.class_name, subclass_count DESC, subclass_name
    """, params)

    subclass_rows = cur.fetchall()

    subclass_map = {}
    for row in subclass_rows:
        class_id = row[0]
        class_name = row[1]
        subclass_name = row[2]
        subclass_count = row[3]

        if class_id not in subclass_map:
            subclass_map[class_id] = {
                "class_name": class_name,
                "subclasses": []
            }

        subclass_map[class_id]["subclasses"].append({
            "subclass_name": subclass_name,
            "count": subclass_count
        })

    subclass_breakdown = [
        {
            "class_id": class_id,
            "class_name": data["class_name"],
            "subclasses": data["subclasses"]
        }
        for class_id, data in subclass_map.items()
    ]

    cur.execute(f"""
        WITH latest_growth AS (
            SELECT DISTINCT ON (cg.character_id)
                cg.character_id,
                cg.level
            FROM character_growth cg
            ORDER BY cg.character_id, cg.time DESC
        ),
        filtered_characters AS (
            SELECT
                c.character_id,
                COALESCE(lg.level, c.starting_level) AS level
            FROM character c
            LEFT JOIN latest_growth lg
                ON c.character_id = lg.character_id
            {where_sql}
        )
        SELECT
            LEAST(cl1.class_name, cl2.class_name) AS class_a,
            GREATEST(cl1.class_name, cl2.class_name) AS class_b,
            COUNT(*) AS combo_count
        FROM character_class cc1
        JOIN character_class cc2
            ON cc1.character_id = cc2.character_id
           AND cc1.class_id < cc2.class_id
        JOIN class cl1
            ON cc1.class_id = cl1.class_id
        JOIN class cl2
            ON cc2.class_id = cl2.class_id
        JOIN filtered_characters fc
            ON cc1.character_id = fc.character_id
        GROUP BY
            LEAST(cl1.class_name, cl2.class_name),
            GREATEST(cl1.class_name, cl2.class_name)
        ORDER BY combo_count DESC, class_a, class_b
    """, params)

    multiclass_rows = cur.fetchall()

    multiclass_combinations = [
        {
            "class_a": row[0],
            "class_b": row[1],
            "count": row[2]
        }
        for row in multiclass_rows
    ]

    cur.close()
    conn.close()

    return jsonify({
        "filters": {
            "tier": tier,
            "active_only": active_only
        },
        "classes": classes,
        "subclass_breakdown": subclass_breakdown,
        "multiclass_combinations": multiclass_combinations
    })

@app.route("/spell-distribution")
def spell_distribution_page():
    return render_template("spell_distribution.html")


@app.route("/api/spell-distribution")
def spell_distribution_api():
    tier = request.args.get("tier", "all").strip().lower()
    class_filters = request.args.getlist("class")
    species_filters = request.args.getlist("species")
    school_filter = request.args.get("school", "all").strip()
    level_filter = request.args.get("level", "any").strip().lower()
    tag_filter = request.args.get("tag", "").strip()
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    conn = get_connection()
    cur = conn.cursor()

    params = []
    filters = []

    growth_cte = """
        WITH filtered_growth AS (
            SELECT
                cg.*,
                s.date AS session_date
            FROM character_growth cg
            LEFT JOIN session s
                ON cg.session_id = s.session_id
        ),
        latest_growth AS (
            SELECT DISTINCT ON (fg.character_id)
                fg.character_id,
                fg.level,
                fg.session_date,
                fg.time
            FROM filtered_growth fg
            ORDER BY fg.character_id, fg.time DESC
        )
    """

    if class_filter != "all":
        filters.append("cl.class_name = %s")
        params.append(class_filter)

    if school_filter != "all":
        filters.append("s.school = %s")
        params.append(school_filter)

    if level_filter != "any":
        filters.append("s.level = %s")
        params.append(int(level_filter))

    if tier != "all":
        filters.append("""
            (
                CASE
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 0 AND 4 THEN 1
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 5 AND 10 THEN 2
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 11 AND 15 THEN 3
                    ELSE 4
                END
            ) = %s
        """)
        params.append(int(tier))

    if tag_filter:
        filters.append("""
            EXISTS (
                SELECT 1
                FROM spell_tag st2
                JOIN tag t2
                    ON st2.tag_id = t2.tag_id
                WHERE st2.spell_id = s.spell_id
                  AND t2.tag_name = %s
            )
        """)
        params.append(tag_filter)

    if date_from:
        filters.append("(lg.session_date IS NULL OR lg.session_date >= %s)")
        params.append(date_from)

    if date_to:
        filters.append("(lg.session_date IS NULL OR lg.session_date <= %s)")
        params.append(date_to)

    where_sql = ""
    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    cur.execute(f"""
        {growth_cte}
        SELECT
            s.spell_id,
            s.spell_name,
            s.level,
            s.school,
            COUNT(DISTINCT sb.character_id) AS known_by_count,
            MIN(t.tag_name) AS primary_tag
        FROM spell s
        LEFT JOIN spellbook sb
            ON s.spell_id = sb.spell_id
        LEFT JOIN character c
            ON sb.character_id = c.character_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN character_class cc
            ON c.character_id = cc.character_id
        LEFT JOIN class cl
            ON cc.class_id = cl.class_id
        LEFT JOIN spell_tag st
            ON s.spell_id = st.spell_id
        LEFT JOIN tag t
            ON st.tag_id = t.tag_id
        {where_sql}
        GROUP BY s.spell_id, s.spell_name, s.level, s.school
        ORDER BY known_by_count DESC, s.spell_name
        LIMIT 20
    """, params)

    top_spell_rows = cur.fetchall()
    top_spells = [
        {
            "spell_id": row[0],
            "spell_name": row[1],
            "level": row[2],
            "school": row[3],
            "known_by": row[4],
            "tag": row[5]
        }
        for row in top_spell_rows
    ]

    cur.execute("SELECT class_name FROM class ORDER BY class_name")
    available_classes = [row[0] for row in cur.fetchall()]

    cur.execute("SELECT DISTINCT school FROM spell ORDER BY school")
    available_schools = [row[0] for row in cur.fetchall()]

    cur.execute("""
        SELECT DISTINCT t.tag_name
        FROM tag t
        JOIN spell_tag st
            ON t.tag_id = st.tag_id
        ORDER BY t.tag_name
    """)
    available_tags = [row[0] for row in cur.fetchall()]

    class_school_params = []
    class_school_filters = []

    if tier != "all":
        class_school_filters.append("""
            (
                CASE
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 0 AND 4 THEN 1
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 5 AND 10 THEN 2
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 11 AND 15 THEN 3
                    ELSE 4
                END
            ) = %s
        """)
        class_school_params.append(int(tier))

    if class_filter != "all":
        class_school_filters.append("cl.class_name = %s")
        class_school_params.append(class_filter)

    if school_filter != "all":
        class_school_filters.append("s.school = %s")
        class_school_params.append(school_filter)

    if level_filter != "any":
        class_school_filters.append("s.level = %s")
        class_school_params.append(int(level_filter))

    if tag_filter:
        class_school_filters.append("""
            EXISTS (
                SELECT 1
                FROM spell_tag st2
                JOIN tag t2
                    ON st2.tag_id = t2.tag_id
                WHERE st2.spell_id = s.spell_id
                  AND t2.tag_name = %s
            )
        """)
        class_school_params.append(tag_filter)

    if date_from:
        class_school_filters.append("(lg.session_date IS NULL OR lg.session_date >= %s)")
        class_school_params.append(date_from)

    if date_to:
        class_school_filters.append("(lg.session_date IS NULL OR lg.session_date <= %s)")
        class_school_params.append(date_to)

    class_school_where = ""
    if class_school_filters:
        class_school_where = "WHERE " + " AND ".join(class_school_filters)

    cur.execute(f"""
        {growth_cte}
        SELECT
            cl.class_name,
            s.school,
            COUNT(*) AS spell_count
        FROM spellbook sb
        JOIN spell s
            ON sb.spell_id = s.spell_id
        JOIN character c
            ON sb.character_id = c.character_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN character_class cc
            ON c.character_id = cc.character_id
        LEFT JOIN class cl
            ON cc.class_id = cl.class_id
        {class_school_where}
        GROUP BY cl.class_name, s.school
        ORDER BY cl.class_name, s.school
    """, class_school_params)

    class_school_rows = cur.fetchall()

    school_names = sorted({row[1] for row in class_school_rows})
    class_names = sorted({row[0] for row in class_school_rows if row[0]})

    school_counts_by_class = {class_name: {school: 0 for school in school_names} for class_name in class_names}
    for class_name, school_name, count in class_school_rows:
        if class_name:
            school_counts_by_class[class_name][school_name] = count

    cur.execute(f"""
        {growth_cte}
        SELECT
            s.level,
            COUNT(*) AS spell_count
        FROM spellbook sb
        JOIN spell s
            ON sb.spell_id = s.spell_id
        JOIN character c
            ON sb.character_id = c.character_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN character_class cc
            ON c.character_id = cc.character_id
        LEFT JOIN class cl
            ON cc.class_id = cl.class_id
        {where_sql}
        GROUP BY s.level
        ORDER BY s.level
    """, params)

    level_rows = cur.fetchall()
    level_distribution = {
        "labels": [row[0] for row in level_rows],
        "values": [row[1] for row in level_rows]
    }

    cross_reference = []
    if tag_filter:
        cur.execute(f"""
            {growth_cte}
            SELECT
                c.character_id,
                c.character_name,
                p.player_name,
                s.spell_id,
                s.spell_name,
                s.level,
                s.school
            FROM spellbook sb
            JOIN spell s
                ON sb.spell_id = s.spell_id
            JOIN character c
                ON sb.character_id = c.character_id
            JOIN player p
                ON c.player_id = p.player_id
            LEFT JOIN latest_growth lg
                ON c.character_id = lg.character_id
            LEFT JOIN character_class cc
                ON c.character_id = cc.character_id
            LEFT JOIN class cl
                ON cc.class_id = cl.class_id
            WHERE EXISTS (
                SELECT 1
                FROM spell_tag st
                JOIN tag t
                    ON st.tag_id = t.tag_id
                WHERE st.spell_id = s.spell_id
                  AND t.tag_name = %s
            )
            ORDER BY c.character_name, s.spell_name
        """, [tag_filter])

        cross_reference = [
            {
                "character_id": row[0],
                "character_name": row[1],
                "player_name": row[2],
                "spell_id": row[3],
                "spell_name": row[4],
                "level": row[5],
                "school": row[6]
            }
            for row in cur.fetchall()
        ]

    cur.execute(f"""
        {growth_cte}
        SELECT
            COUNT(*) AS total_known_spells,
            COUNT(DISTINCT sb.character_id) AS total_casters,
            AVG(CASE WHEN s.is_concentration THEN 1 ELSE 0 END) * 100 AS concentration_pct
        FROM spellbook sb
        JOIN spell s
            ON sb.spell_id = s.spell_id
        JOIN character c
            ON sb.character_id = c.character_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN character_class cc
            ON c.character_id = cc.character_id
        LEFT JOIN class cl
            ON cc.class_id = cl.class_id
        {where_sql}
    """, params)

    stats_row = cur.fetchone()
    total_known_spells = stats_row[0] or 0
    total_casters = stats_row[1] or 0
    concentration_pct = round(stats_row[2] or 0, 1)

    cur.execute(f"""
        {growth_cte}
        SELECT
            s.school,
            COUNT(*) AS school_count
        FROM spellbook sb
        JOIN spell s
            ON sb.spell_id = s.spell_id
        JOIN character c
            ON sb.character_id = c.character_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN character_class cc
            ON c.character_id = cc.character_id
        LEFT JOIN class cl
            ON cc.class_id = cl.class_id
        {where_sql}
        GROUP BY s.school
        ORDER BY school_count DESC
        LIMIT 1
    """, params)

    school_row = cur.fetchone()
    most_common_school = school_row[0] if school_row else "N/A"

    avg_spells_per_caster = round(total_known_spells / total_casters, 1) if total_casters else 0

    cur.close()
    conn.close()

    return jsonify({
        "filters": {
            "tier": tier,
            "class": class_filter,
            "school": school_filter,
            "level": level_filter,
            "tag": tag_filter,
            "date_from": date_from,
            "date_to": date_to,
            "available_classes": available_classes,
            "available_schools": available_schools,
            "available_tags": available_tags
        },
        "top_spells": top_spells,
        "top_spells_chart": {
            "labels": [row["spell_name"] for row in top_spells[:10]],
            "values": [row["known_by"] for row in top_spells[:10]]
        },
        "class_school_distribution": {
            "classes": class_names,
            "schools": school_names,
            "datasets": [
                {
                    "school": school,
                    "values": [school_counts_by_class[class_name][school] for class_name in class_names]
                }
                for school in school_names
            ]
        },
        "level_distribution": level_distribution,
        "cross_reference": cross_reference,
        "insights": {
            "most_common_school": most_common_school,
            "average_spells_per_caster": avg_spells_per_caster,
            "concentration_pct": concentration_pct,
            "total_known_spells": total_known_spells
        }
    })


@app.route("/species-breakdown")
def species_breakdown_page():
    return render_template("species_breakdown.html")


@app.route("/api/species-breakdown")
def species_breakdown_api():
    tier = request.args.get("tier", "all").strip().lower()
    active_only = request.args.get("active_only", "true").lower() == "true"
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    selected_species = [s.strip() for s in request.args.getlist("species") if s.strip()]
    selected_classes = [c.strip() for c in request.args.getlist("class") if c.strip()]

    conn = get_connection()
    cur = conn.cursor()

    filters = []
    params = []

    if active_only:
        filters.append("c.is_active = TRUE")

    if tier != "all":
        filters.append("""
            (
                CASE
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 0 AND 4 THEN 1
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 5 AND 10 THEN 2
                    WHEN COALESCE(lg.level, c.starting_level) BETWEEN 11 AND 15 THEN 3
                    ELSE 4
                END
            ) = %s
        """)
        params.append(int(tier))

    if selected_species:
        filters.append("r.race_name = ANY(%s)")
        params.append(selected_species)

    if selected_classes:
        filters.append("""
            EXISTS (
                SELECT 1
                FROM character_class ccx
                JOIN class clx
                    ON ccx.class_id = clx.class_id
                WHERE ccx.character_id = c.character_id
                  AND clx.class_name = ANY(%s)
            )
        """)
        params.append(selected_classes)

    if date_from:
        filters.append("(lg.session_date IS NULL OR lg.session_date >= %s)")
        params.append(date_from)

    if date_to:
        filters.append("(lg.session_date IS NULL OR lg.session_date <= %s)")
        params.append(date_to)

    where_sql = ""
    if filters:
        where_sql = "WHERE " + " AND ".join(filters)

    base_cte = f"""
        WITH latest_growth AS (
            SELECT DISTINCT ON (cg.character_id)
                cg.character_id,
                cg.level,
                cg.hit_points,
                cg.armor_class,
                cg.passive_perception,
                cg.strength,
                cg.dexterity,
                cg.constitution,
                cg.intelligence,
                cg.wisdom,
                cg.charisma,
                cg.gold,
                s.date AS session_date,
                cg.time
            FROM character_growth cg
            LEFT JOIN session s
                ON cg.session_id = s.session_id
            ORDER BY cg.character_id, cg.time DESC
        ),
        filtered_characters AS (
            SELECT
                c.character_id,
                c.character_name,
                c.picture_url,
                c.player_id,
                p.player_name,
                r.race_name AS species_name,
                COALESCE(lg.level, c.starting_level) AS level,
                COALESCE(lg.hit_points, 0) AS hit_points,
                COALESCE(lg.armor_class, 0) AS armor_class,
                COALESCE(lg.passive_perception, 0) AS passive_perception,
                COALESCE(lg.strength, 0) AS strength,
                COALESCE(lg.dexterity, 0) AS dexterity,
                COALESCE(lg.constitution, 0) AS constitution,
                COALESCE(lg.intelligence, 0) AS intelligence,
                COALESCE(lg.wisdom, 0) AS wisdom,
                COALESCE(lg.charisma, 0) AS charisma,
                COALESCE(lg.gold, 0) AS gold,
                c.is_active
            FROM character c
            JOIN player p
                ON c.player_id = p.player_id
            JOIN race r
                ON c.race_id = r.race_id
            LEFT JOIN latest_growth lg
                ON c.character_id = lg.character_id
            {where_sql}
        )
    """

    # available species
    cur.execute("SELECT race_name FROM race ORDER BY race_name")
    available_species = [row[0] for row in cur.fetchall()]

    # available classes
    cur.execute("SELECT class_name FROM class ORDER BY class_name")
    available_classes = [row[0] for row in cur.fetchall()]

    # quick stats + population
    cur.execute(f"""
        {base_cte}
        SELECT
            species_name,
            COUNT(*) AS species_count
        FROM filtered_characters
        GROUP BY species_name
        ORDER BY species_count DESC, species_name
    """, params)

    species_population_rows = cur.fetchall()

    species_population = [
        {"species_name": row[0], "count": row[1]}
        for row in species_population_rows
    ]

    species_count = len(species_population)
    most_common = species_population[0] if species_population else None

    least_common = None
    if species_population:
        min_count = min(row["count"] for row in species_population if row["count"] > 0)
        tied = [row["species_name"] for row in species_population if row["count"] == min_count]
        least_common = {
            "species_names": tied,
            "count": min_count
        }

    # heatmap
    cur.execute(f"""
        {base_cte},
        class_rows AS (
            SELECT
                fc.species_name,
                cl.class_name,
                COUNT(DISTINCT fc.character_id) AS combo_count
            FROM filtered_characters fc
            JOIN character_class cc
                ON fc.character_id = cc.character_id
            JOIN class cl
                ON cc.class_id = cl.class_id
            GROUP BY fc.species_name, cl.class_name
        )
        SELECT
            species_name,
            class_name,
            combo_count
        FROM class_rows
        ORDER BY species_name, class_name
    """, params)

    heatmap_rows = cur.fetchall()

    heatmap_species = sorted({row[0] for row in heatmap_rows})
    heatmap_classes = sorted({row[1] for row in heatmap_rows})

    heatmap_map = {
        species: {cls: 0 for cls in heatmap_classes}
        for species in heatmap_species
    }

    for species_name, class_name, combo_count in heatmap_rows:
        heatmap_map[species_name][class_name] = combo_count

    heatmap_values = [
        [heatmap_map[species][cls] for cls in heatmap_classes]
        for species in heatmap_species
    ]

    # tier distribution
    cur.execute(f"""
        {base_cte}
        SELECT
            species_name,
            CASE
                WHEN level BETWEEN 0 AND 4 THEN 1
                WHEN level BETWEEN 5 AND 10 THEN 2
                WHEN level BETWEEN 11 AND 15 THEN 3
                ELSE 4
            END AS tier_bucket,
            COUNT(*) AS tier_count
        FROM filtered_characters
        GROUP BY species_name, tier_bucket
        ORDER BY species_name, tier_bucket
    """, params)

    tier_rows = cur.fetchall()

    tier_species = sorted({row[0] for row in tier_rows})
    tier_map = {
        species: {1: 0, 2: 0, 3: 0, 4: 0}
        for species in tier_species
    }

    for species_name, tier_bucket, tier_count in tier_rows:
        tier_map[species_name][tier_bucket] = tier_count

    tier_distribution = {
        "labels": tier_species,
        "datasets": [
            {"label": "Tier 1", "values": [tier_map[species][1] for species in tier_species]},
            {"label": "Tier 2", "values": [tier_map[species][2] for species in tier_species]},
            {"label": "Tier 3", "values": [tier_map[species][3] for species in tier_species]},
            {"label": "Tier 4", "values": [tier_map[species][4] for species in tier_species]}
        ]
    }

    # character grid
    cur.execute(f"""
        {base_cte},
        class_agg AS (
            SELECT
                character_id,
                STRING_AGG(class_display, ' / ' ORDER BY class_name) AS class_display,
                ARRAY_AGG(class_name ORDER BY class_name) AS class_names
            FROM (
                SELECT DISTINCT
                    cc.character_id,
                    cl.class_name,
                    cl.class_name || COALESCE(' (' || sc.subclass_name || ')', '') AS class_display
                FROM character_class cc
                JOIN class cl
                    ON cc.class_id = cl.class_id
                LEFT JOIN subclass sc
                    ON cc.subclass_id = sc.subclass_id
            ) class_distinct
            GROUP BY character_id
        )
        SELECT
            fc.character_id,
            fc.character_name,
            fc.picture_url,
            fc.player_id,
            fc.player_name,
            fc.species_name,
            fc.level,
            fc.hit_points,
            fc.armor_class,
            fc.passive_perception,
            fc.strength,
            fc.dexterity,
            fc.constitution,
            fc.intelligence,
            fc.wisdom,
            fc.charisma,
            ca.class_display,
            ca.class_names
        FROM filtered_characters fc
        LEFT JOIN class_agg ca
            ON fc.character_id = ca.character_id
        ORDER BY fc.species_name, fc.character_name
    """, params)

    character_rows = cur.fetchall()

    characters = []
    for row in character_rows:
        characters.append({
            "character_id": row[0],
            "character_name": row[1],
            "avatar": row[2],
            "player_id": row[3],
            "player_name": row[4],
            "species_name": row[5],
            "level": row[6],
            "hit_points": row[7],
            "armor_class": row[8],
            "passive_perception": row[9],
            "strength": row[10],
            "dexterity": row[11],
            "constitution": row[12],
            "intelligence": row[13],
            "wisdom": row[14],
            "charisma": row[15],
            "class_display": row[16] or "Unknown",
            "class_names": row[17] or []
        })

    insights = build_species_insights(
        species_population=species_population,
        heatmap_rows=heatmap_rows,
        tier_map=tier_map,
        active_only=active_only
    )

    cur.close()
    conn.close()

    return jsonify({
        "filters": {
            "tier": tier,
            "classes": selected_classes,
            "species": selected_species,
            "active_only": active_only,
            "date_from": date_from,
            "date_to": date_to,
            "available_classes": available_classes,
            "available_species": available_species
        },
        "quick_stats": {
            "species_count": species_count,
            "most_common": most_common,
            "least_common": least_common
        },
        "species_population": species_population,
        "species_class_heatmap": {
            "species": heatmap_species,
            "classes": heatmap_classes,
            "values": heatmap_values
        },
        "tier_distribution": tier_distribution,
        "characters": characters,
        "insights": insights
    })


def build_species_insights(species_population, heatmap_rows, tier_map, active_only):
    insights = []

    if species_population:
        most_common = species_population[0]
        insights.append(
            f"{most_common['species_name']} is the most represented species in the current filtered view ({most_common['count']})."
        )

        min_count = min(row["count"] for row in species_population if row["count"] > 0)
        least_common_species = [row["species_name"] for row in species_population if row["count"] == min_count]
        if least_common_species:
            label = ", ".join(least_common_species)
            suffix = "active species" if active_only else "species"
            insights.append(
                f"{label} {'is' if len(least_common_species) == 1 else 'are'} currently the least represented {suffix} ({min_count})."
            )

    widest_species = None
    widest_tier_count = -1
    widest_total = -1

    for species_name, tier_counts in tier_map.items():
        non_zero_tiers = sum(1 for count in tier_counts.values() if count > 0)
        total = sum(tier_counts.values())
        if non_zero_tiers > widest_tier_count or (non_zero_tiers == widest_tier_count and total > widest_total):
            widest_species = species_name
            widest_tier_count = non_zero_tiers
            widest_total = total

    if widest_species and widest_tier_count > 0:
        insights.append(
            f"{widest_species} is represented across {widest_tier_count} tier{'s' if widest_tier_count != 1 else ''} in the current filtered set."
        )

    species_class_counts = defaultdict(lambda: defaultdict(int))
    for species_name, class_name, combo_count in heatmap_rows:
        species_class_counts[species_name][class_name] = combo_count

    association_lines = []
    for species_name, class_counts in species_class_counts.items():
        total = sum(class_counts.values())
        if total < 3:
            continue

        sorted_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)
        top_class, top_count = sorted_classes[0]
        top_share = top_count / total

        if top_share >= 0.5:
            association_lines.append(
                f"{species_name} appears most often in {top_class} builds."
            )
            continue

        if len(sorted_classes) > 1:
            second_class, second_count = sorted_classes[1]
            if (top_count + second_count) / total >= 0.7:
                association_lines.append(
                    f"{species_name} is mostly represented in {top_class} and {second_class} combinations."
                )

    insights.extend(association_lines[:2])

    return insights[:5]

if __name__ == "__main__":
    app.run(debug=True)