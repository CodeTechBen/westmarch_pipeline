fetch(`/api/spell/${spellId}`)
    .then(res => {
        if (!res.ok) {
            throw new Error("Failed to load spell data");
        }
        return res.json();
    })
    .then(data => {
        populateSpellHeader(data.spell);
        populateSpellMeta(data.spell);
        populateSpellDescription(data.spell);
        populateTags(data.tags);
        populateKnownBy(data.known_by);
    })
    .catch(error => {
        console.error(error);
        document.getElementById("spell-title").textContent = "Could not load spell";
    });

function populateSpellHeader(spell) {
    document.getElementById("spell-title").textContent = spell.name;
    document.getElementById("spell-subtitle").textContent =
        `${formatSpellLevel(spell.level)} ${spell.school}`;
}

function populateSpellMeta(spell) {
    document.getElementById("spell-casting-time").textContent = spell.casting_time || "-";
    document.getElementById("spell-range").textContent = spell.range || "-";
    document.getElementById("spell-duration").textContent = spell.duration || "-";
    document.getElementById("spell-components").textContent = spell.components || "-";
    document.getElementById("spell-concentration").textContent = spell.is_concentration ? "Yes" : "No";
    document.getElementById("spell-ritual").textContent = spell.is_ritual ? "Yes" : "No";
}

function populateSpellDescription(spell) {
    document.getElementById("spell-description").textContent = spell.description || "";
}

function populateTags(tags) {
    const container = document.getElementById("spell-tags");
    container.innerHTML = "";

    if (!tags.length) {
        container.innerHTML = "<p>No tags found for this spell.</p>";
        return;
    }

    tags.forEach(tag => {
        const span = document.createElement("span");
        span.className = "spell-tag-pill";
        span.textContent = tag;
        container.appendChild(span);
    });
}

function populateKnownBy(knownBy) {
    const tbody = document.getElementById("spell-known-body");
    const count = document.getElementById("known-count");

    tbody.innerHTML = "";
    count.textContent = `(${knownBy.length})`;

    if (!knownBy.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5">No characters found for this spell.</td>
            </tr>
        `;
        return;
    }

    knownBy.forEach(row => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td><a class="character-link" href="/character/${row.character_id}">${row.character_name}</a></td>
            <td><a class="player-link" href="/player/${row.player_id}">${row.player_name}</a></td>
            <td>${row.class_display}</td>
            <td>${row.level ?? "-"}</td>
            <td>${row.is_active ? "✓" : "✗"}</td>
        `;

        tbody.appendChild(tr);
    });
}

function formatSpellLevel(level) {
    if (level === 0) return "Cantrip";

    const suffixes = {
        1: "1st Level",
        2: "2nd Level",
        3: "3rd Level"
    };

    return suffixes[level] || `${level}th Level`;
}