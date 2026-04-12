from flask import Flask, render_template, jsonify, request
from db import get_connection

app = Flask(__name__)

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

    # Characters
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

    # Players
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

    # Spells
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

    # Items
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

    # Sessions
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

    # ----------------------------
    # Items
    # ----------------------------
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

    # ----------------------------
    # Spells
    # ----------------------------
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

    # ----------------------------
    # Characters
    # ----------------------------
    if filter_type in ("all", "characters"):
        cur.execute("""
            WITH healing_spells AS (
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
            )
            SELECT
                c.character_id,
                c.character_name,
                p.player_name,
                COALESCE(cl.class_name, 'Unknown') AS class_name,
                COALESCE(lg.level, c.starting_level) AS level,
                COUNT(DISTINCT hs.spell_id) AS healing_spell_count,
                COUNT(DISTINCT hi.item_id) AS healing_item_count
            FROM character c
            JOIN player p
                ON c.player_id = p.player_id
            LEFT JOIN latest_growth lg
                ON c.character_id = lg.character_id
            LEFT JOIN character_class cc
                ON c.character_id = cc.character_id
            LEFT JOIN class cl
                ON cc.class_id = cl.class_id
            LEFT JOIN healing_spells hs
                ON c.character_id = hs.character_id
            LEFT JOIN healing_items hi
                ON c.character_id = hi.character_id
            WHERE c.character_name ILIKE %s
               OR p.player_name ILIKE %s
               OR cl.class_name ILIKE %s
               OR hs.spell_id IS NOT NULL
               OR hi.item_id IS NOT NULL
            GROUP BY
                c.character_id,
                c.character_name,
                p.player_name,
                cl.class_name,
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

    cur.execute("""SELECT * FROM session_summary ORDER BY date DESC""")

    rows = cur.fetchall()

    cur.close()
    conn.close()

    sessions = []
    for r in rows:
        sessions.append({
            "id": r[0],
            "name": r[1],
            "date": r[2].strftime("%Y-%m-%d"),
            "dm": r[3],
            "players": r[4],
            "tier": f"Tier {r[5]}" if r[5] else "Unknown"
        })

    return jsonify(sessions)

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

    return jsonify(dms)

@app.route("/sessions")
def sessions_page():
    return render_template("sessions.html")

@app.route("/api/session/<int:session_id>")
def session_detail_api(session_id):
    conn = get_connection()
    cur = conn.cursor()

    # Session info
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

    # Character data for this session
    cur.execute("""
        SELECT 
            c.character_id,
            c.character_name,
            c.picture_url,
            p.player_name,
            p.player_id,
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
        WHERE cg.session_id = %s
        ORDER BY c.character_name
    """, (session_id,))
    characters = cur.fetchall()

    # Tier calculation from session character levels
    tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}

    for c in characters:
        level = c[4]
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

    # Item distribution by rarity
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

    # Transform character data
    char_data = []
    for c in characters:
        char_data.append({
            "id": c[0],
            "name": c[1],
            "avatar": c[2],
            "player": c[3],
            "player_id": c[4],
            "level": c[5],
            "hp": c[6],
            "ac": c[7],
            "pp": c[8],
            "stats": {
                "STR": c[9],
                "DEX": c[10],
                "CON": c[11],
                "INT": c[12],
                "WIS": c[13],
                "CHA": c[14]
            },
            "gold": c[15]
        })

    # Build item table map
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

    # Recommendation logic
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

    cur.execute("""
        WITH latest_growth AS (
            SELECT DISTINCT ON (cg.character_id)
                cg.character_id,
                cg.level
            FROM character_growth cg
            ORDER BY cg.character_id, cg.time DESC
        )
        SELECT DISTINCT
            c.character_id,
            c.character_name,
            p.player_id,
            p.player_name,
            cl.class_name,
            sc.subclass_name,
            COALESCE(cg_spell.level, lg.level, c.starting_level) AS character_level,
            c.is_active
        FROM spellbook sb
        JOIN character c
            ON sb.character_id = c.character_id
        JOIN player p
            ON c.player_id = p.player_id
        LEFT JOIN character_class cc
            ON c.character_id = cc.character_id
        LEFT JOIN class cl
            ON cc.class_id = cl.class_id
        LEFT JOIN subclass sc
            ON cc.subclass_id = sc.subclass_id
        LEFT JOIN character_growth cg_spell
            ON sb.growth_id = cg_spell.growth_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
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
            "class_display": (
                f"{row[4]}/{row[5]}" if row[4] and row[5]
                else row[4] or "Unknown"
            ),
            "level": row[6],
            "is_active": row[7]
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

    # ----------------------------
    # Player info
    # ----------------------------
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

    # ----------------------------
    # Total sessions played
    # ----------------------------
    cur.execute("""
        SELECT COUNT(DISTINCT cg.session_id)
        FROM character_growth cg
        JOIN character c
            ON cg.character_id = c.character_id
        WHERE c.player_id = %s
          AND cg.session_id IS NOT NULL
    """, (player_id,))
    sessions_played = cur.fetchone()[0]

    # ----------------------------
    # Character summary cards
    # latest growth snapshot per character
    # ----------------------------
    cur.execute("""
        WITH latest_growth AS (
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
        )
        SELECT
            c.character_id,
            c.character_name,
            c.picture_url,
            c.is_active,
            r.race_name,
            cl.class_name,
            sc.subclass_name,
            lg.level,
            lg.hit_points,
            lg.gold,
            COALESCE(scnt.session_count, 0) AS session_count
        FROM character c
        JOIN race r
            ON c.race_id = r.race_id
        LEFT JOIN character_class cc
            ON c.character_id = cc.character_id
        LEFT JOIN class cl
            ON cc.class_id = cl.class_id
        LEFT JOIN subclass sc
            ON cc.subclass_id = sc.subclass_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN session_counts scnt
            ON c.character_id = scnt.character_id
        WHERE c.player_id = %s
        ORDER BY c.is_active DESC, c.character_name
    """, (player_id,))
    characters = cur.fetchall()

    # ----------------------------
    # Sessions per month chart
    # ----------------------------
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

    # ----------------------------
    # Recent sessions
    # ----------------------------
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

    # ----------------------------
    # Transform character data
    # ----------------------------
    character_data = []
    for row in characters:
        character_id = row[0]
        character_name = row[1]
        picture_url = row[2]
        is_active = row[3]
        race_name = row[4]
        class_name = row[5]
        subclass_name = row[6]
        level = row[7]
        hit_points = row[8]
        gold = row[9]
        session_count = row[10]

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

        subtitle = f"{race_name} {class_name or 'Unknown Class'}"
        if level is not None:
            subtitle += f" {level}"
        if subclass_name:
            subtitle += f" ({subclass_name})"

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

    # ----------------------------
    # Transform chart data
    # ----------------------------
    chart_labels = [row[0] for row in sessions_per_month]
    chart_values = [row[1] for row in sessions_per_month]

    # ----------------------------
    # Transform recent sessions
    # ----------------------------
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

    # ----------------------------
    # Core character + latest growth snapshot
    # ----------------------------
    cur.execute("""
        WITH latest_growth AS (
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
        )
        SELECT
            c.character_id,
            c.character_name,
            c.picture_url,
            c.dnd_beyond_id,
            c.is_active,
            p.player_id,
            p.player_name,
            r.race_name,
            cl.class_name,
            sc.subclass_name,
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
        LEFT JOIN character_class cc
            ON c.character_id = cc.character_id
        LEFT JOIN class cl
            ON cc.class_id = cl.class_id
        LEFT JOIN subclass sc
            ON cc.subclass_id = sc.subclass_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN session_count scnt
            ON c.character_id = scnt.character_id
        WHERE c.character_id = %s
    """, (character_id, character_id, character_id))
    character = cur.fetchone()

    if not character:
        cur.close()
        conn.close()
        return jsonify({"error": "Character not found"}), 404

    # ----------------------------
    # Growth over time
    # ----------------------------
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

    # ----------------------------
    # Inventory from latest growth if possible, else by character
    # ----------------------------
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

    # ----------------------------
    # Spellbook from latest growth if possible, else by character
    # ----------------------------
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

    # ----------------------------
    # Session history
    # ----------------------------
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

    # ----------------------------
    # Derived fields
    # ----------------------------
    level = character[10]
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
            "subclass_name": character[9],
            "level": character[10],
            "strength": character[11],
            "dexterity": character[12],
            "constitution": character[13],
            "intelligence": character[14],
            "wisdom": character[15],
            "charisma": character[16],
            "hit_points": character[17],
            "gold": character[18],
            "passive_perception": character[19],
            "armor_class": character[20],
            "sessions_played": character[21],
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

    # ----------------------------
    # Item core details
    # ----------------------------
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

    # ----------------------------
    # Item tags
    # ----------------------------
    cur.execute("""
        SELECT t.tag_name
        FROM item_tag it
        JOIN tag t
            ON it.tag_id = t.tag_id
        WHERE it.item_id = %s
        ORDER BY t.tag_name
    """, (item_id,))
    tags = [row[0] for row in cur.fetchall()]

    # ----------------------------
    # Characters who own this item
    # Uses latest growth snapshot if available for class/level context
    # ----------------------------
    cur.execute("""
        WITH latest_growth AS (
            SELECT DISTINCT ON (cg.character_id)
                cg.character_id,
                cg.level,
                cg.time
            FROM character_growth cg
            ORDER BY cg.character_id, cg.time DESC
        )
        SELECT
            c.character_id,
            c.character_name,
            p.player_id,
            p.player_name,
            cl.class_name,
            sc.subclass_name,
            COALESCE(SUM(inv.quantity), 0) AS qty,
            c.is_active
        FROM inventory inv
        JOIN character c
            ON inv.character_id = c.character_id
        JOIN player p
            ON c.player_id = p.player_id
        LEFT JOIN latest_growth lg
            ON c.character_id = lg.character_id
        LEFT JOIN character_class cc
            ON c.character_id = cc.character_id
        LEFT JOIN class cl
            ON cc.class_id = cl.class_id
        LEFT JOIN subclass sc
            ON cc.subclass_id = sc.subclass_id
        WHERE inv.item_id = %s
        GROUP BY
            c.character_id,
            c.character_name,
            p.player_id,
            p.player_name,
            cl.class_name,
            sc.subclass_name,
            c.is_active
        ORDER BY c.is_active DESC, c.character_name
    """, (item_id,))
    owner_rows = cur.fetchall()

    # ----------------------------
    # Campaign-wide rarity distribution
    # ----------------------------
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
            "class_display": (
                f"{row[4]}/{row[5]}" if row[4] and row[5]
                else row[4] or "Unknown"
            ),
            "quantity": row[6],
            "is_active": row[7]
        })

    rarity_labels = [row[0] for row in rarity_rows]
    rarity_values = [row[1] for row in rarity_rows]

    # Placeholder description until you add one to schema
    # Your current item table does not include a description column
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

if __name__ == "__main__":
    app.run(debug=True)