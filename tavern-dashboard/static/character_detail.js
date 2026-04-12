fetch(`/api/character/${characterId}`)
    .then(res => {
        if (!res.ok) {
            throw new Error("Failed to load character data");
        }
        return res.json();
    })
    .then(data => {
        populateHeader(data.character);
        populateAbilityScores(data.character);
        populateStats(data.character);
        populateGrowthChart(data.growth);
        populateInventory(data.inventory);
        populateSpellbook(data.spells, data.character.class_name);
        populateSessionHistory(data.session_history);
    })
    .catch(error => {
        console.error(error);
        const title = document.getElementById("character-name");
        if (title) {
            title.textContent = "Could not load character";
        }
    });

function populateHeader(character) {
    document.getElementById("character-name").textContent = character.name.toUpperCase();
    document.getElementById("character-subtitle").textContent =
        `${character.race_name} ${character.class_name}${character.subclass_name ? ` (${character.subclass_name})` : ""}`;

    const metaLine = document.getElementById("character-meta-line");
    metaLine.textContent =
        `Level ${character.level} | ${character.tier} | ${character.is_active ? "Active ✓" : "Inactive ✗"}`;

    const playerLink = document.getElementById("character-player-link");
    playerLink.textContent = character.player_name;
    playerLink.href = `/player/${character.player_id}`;

    document.getElementById("character-sessions-played").textContent =
        `| Sessions Played: ${character.sessions_played}`;

    const avatar = document.getElementById("character-avatar");
    avatar.src = character.avatar || "/static/default-avatar.svg";
    avatar.alt = character.name;
    avatar.onerror = () => {
        avatar.src = "/static/default-avatar.svg";
    };

    const beyondLink = document.getElementById("dnd-beyond-link");
    if (character.dnd_beyond_id) {
        beyondLink.href = `https://www.dndbeyond.com/characters/${character.dnd_beyond_id}`;
        beyondLink.style.display = "inline-block";
    } else {
        beyondLink.style.display = "none";
    }
}

function populateAbilityScores(character) {
    const container = document.getElementById("ability-grid");
    container.innerHTML = "";

    const abilities = [
        ["STR", character.strength],
        ["DEX", character.dexterity],
        ["CON", character.constitution],
        ["INT", character.intelligence],
        ["WIS", character.wisdom],
        ["CHA", character.charisma]
    ];

    abilities.forEach(([label, score]) => {
        const modifier = calculateModifier(score);

        const card = document.createElement("div");
        card.className = "ability-card";

        card.innerHTML = `
            <div class="ability-label">${label}</div>
            <div class="ability-score">${score}</div>
            <div class="ability-modifier">${formatModifier(modifier)}</div>
        `;

        container.appendChild(card);
    });
}

function populateStats(character) {
    document.getElementById("character-hp").textContent = character.hit_points ?? "-";
    document.getElementById("character-ac").textContent = character.armor_class ?? "-";
    document.getElementById("character-pp").textContent = character.passive_perception ?? "-";
    document.getElementById("character-gold").textContent = character.gold ?? 0;
}

function populateGrowthChart(growth) {
    const canvas = document.getElementById("characterGrowthChart");

    if (!growth.labels.length) {
        canvas.parentElement.innerHTML = "<p>No growth history found for this character.</p>";
        return;
    }

    new Chart(canvas, {
        type: "line",
        data: {
            labels: growth.labels,
            datasets: [
                {
                    label: "HP",
                    data: growth.hp
                },
                {
                    label: "Gold",
                    data: growth.gold
                },
                {
                    label: "Level",
                    data: growth.level
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: "index",
                intersect: false
            },
            plugins: {
                legend: {
                    display: true
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

function populateInventory(inventory) {
    const list = document.getElementById("inventory-list");
    const count = document.getElementById("inventory-count");

    list.innerHTML = "";
    count.textContent = `(${inventory.length} items)`;

    if (!inventory.length) {
        list.innerHTML = "<div>No items found.</div>";
        return;
    }

    inventory.forEach(item => {
        const row = document.createElement("div");
        row.className = "asset-list-item";

        row.innerHTML = `
            <a href="/item/${item.item_id}" class="asset-link">
                ${item.item_name}
            </a>
            <span class="asset-meta">[${item.rarity}]${item.quantity > 1 ? ` x${item.quantity}` : ""}</span>
        `;

        list.appendChild(row);
    });
}

function populateSpellbook(spells, className) {
    const list = document.getElementById("spell-list");
    const count = document.getElementById("spell-count");

    list.innerHTML = "";

    if (!spells.length) {
        count.textContent = "";
        list.innerHTML = `<div>No spells known${className ? ` - ${className}` : ""}</div>`;
        return;
    }

    count.textContent = `(${spells.length})`;

    spells.forEach(spell => {
        const row = document.createElement("div");
        row.className = "asset-list-item";

        row.innerHTML = `
            <a href="/spell/${spell.spell_id}" class="asset-link">
                ✨ ${spell.spell_name}
            </a>
            <span class="asset-meta">[Level ${spell.level} ${spell.school}]</span>
        `;

        list.appendChild(row);
    });
}

function populateSessionHistory(sessionHistory) {
    const tbody = document.getElementById("character-session-history-body");
    tbody.innerHTML = "";

    if (!sessionHistory.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5">No session history found.</td>
            </tr>
        `;
        return;
    }

    sessionHistory.forEach(row => {
        const levelChange =
            row.level_before !== null && row.level_after !== null
                ? `${row.level_before}→${row.level_after}`
                : (row.level_after ?? "-");

        const goldChange =
            row.gold_change !== null && row.gold_change !== undefined
                ? row.gold_change
                : "-";

        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td><a href="/session/${row.session_id}" class="session-link">${row.session_name}</a></td>
            <td>${row.date}</td>
            <td>${row.dm_name || "Unknown"}</td>
            <td>${levelChange}</td>
            <td>${goldChange}</td>
        `;

        tbody.appendChild(tr);
    });
}

function calculateModifier(score) {
    return Math.floor((score - 10) / 2);
}

function formatModifier(modifier) {
    return modifier >= 0 ? `+${modifier}` : `${modifier}`;
}