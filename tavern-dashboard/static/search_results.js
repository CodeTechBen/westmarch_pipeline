const params = new URLSearchParams(window.location.search);
const initialQuery = params.get("q") || "";
let currentFilter = params.get("type") || "all";

const searchInput = document.getElementById("search-page-input");
const searchButton = document.getElementById("search-page-button");
const filterButtons = document.querySelectorAll(".search-filter-btn");

searchInput.value = initialQuery;

filterButtons.forEach(btn => {
    if (btn.dataset.filter === currentFilter) {
        btn.classList.add("active");
    } else {
        btn.classList.remove("active");
    }

    btn.addEventListener("click", () => {
        currentFilter = btn.dataset.filter;
        updateFilterButtons();
        runSearch();
    });
});

searchButton.addEventListener("click", () => {
    runSearch(true);
});

searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
        runSearch(true);
    }
});

if (initialQuery) {
    runSearch();
}

function updateFilterButtons() {
    filterButtons.forEach(btn => {
        btn.classList.toggle("active", btn.dataset.filter === currentFilter);
    });
}

function runSearch(updateUrl = false) {
    const query = searchInput.value.trim();

    if (!query) {
        clearResults();
        document.getElementById("search-page-title").textContent = "Search";
        return;
    }

    if (updateUrl) {
        const newUrl = `/search?q=${encodeURIComponent(query)}&type=${encodeURIComponent(currentFilter)}`;
        window.history.pushState({}, "", newUrl);
    }

    fetch(`/api/search/full?q=${encodeURIComponent(query)}&type=${encodeURIComponent(currentFilter)}`)
        .then(res => {
            if (!res.ok) {
                throw new Error("Failed to load search results");
            }
            return res.json();
        })
        .then(data => {
            populateSearchPage(data);
        })
        .catch(error => {
            console.error(error);
            document.getElementById("search-page-title").textContent = "Could not load search results";
        });
}

function populateSearchPage(data) {
    document.getElementById("search-page-title").textContent = `Search: "${data.query}"`;

    populateTags(data.available_tags);
    populateItems(data.items);
    populateSpells(data.spells);
    populateCharacters(data.characters);

    toggleSections();
}

function populateTags(tags) {
    const container = document.getElementById("search-tags");
    container.innerHTML = "";

    if (!tags.length) {
        container.innerHTML = `<span class="search-tag-pill muted">No tags</span>`;
        return;
    }

    tags.forEach(tag => {
        const span = document.createElement("span");
        span.className = "search-tag-pill";
        span.textContent = tag;
        container.appendChild(span);
    });
}

function populateItems(items) {
    document.getElementById("items-count").textContent = `(${items.length} results)`;

    const container = document.getElementById("items-results");
    container.innerHTML = "";

    if (!items.length) {
        container.innerHTML = `<div class="search-empty">No item results.</div>`;
        return;
    }

    items.forEach(item => {
        const card = document.createElement("a");
        card.className = "search-result-card";
        card.href = `/item/${item.item_id}`;

        card.innerHTML = `
            <div class="search-result-main">${item.item_name}</div>
            <div class="search-result-meta">[${item.rarity}]</div>
            <div class="search-result-side">Owned by: ${item.owned_by_count}</div>
        `;

        container.appendChild(card);
    });
}

function populateSpells(spells) {
    document.getElementById("spells-count").textContent = `(${spells.length} results)`;

    const container = document.getElementById("spells-results");
    container.innerHTML = "";

    if (!spells.length) {
        container.innerHTML = `<div class="search-empty">No spell results.</div>`;
        return;
    }

    spells.forEach(spell => {
        const card = document.createElement("a");
        card.className = "search-result-card";
        card.href = `/spell/${spell.spell_id}`;

        card.innerHTML = `
            <div class="search-result-main">${spell.spell_name}</div>
            <div class="search-result-meta">[${formatSpellLevel(spell.level)}]</div>
            <div class="search-result-side">Known by: ${spell.known_by_count} characters</div>
        `;

        container.appendChild(card);
    });
}

function populateCharacters(characters) {
    document.getElementById("characters-count").textContent = `(${characters.length} results)`;

    const tbody = document.getElementById("characters-results-body");
    tbody.innerHTML = "";

    if (!characters.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5">No character results.</td>
            </tr>
        `;
        return;
    }

    characters.forEach(character => {
        const tr = document.createElement("tr");

        tr.innerHTML = `
            <td><a href="/character/${character.character_id}" class="character-link">${character.character_name}</a></td>
            <td>${character.player_name}</td>
            <td>${character.class_display}</td>
            <td>${character.healing_spell_count}</td>
            <td>${character.healing_item_count}</td>
        `;

        tbody.appendChild(tr);
    });
}

function toggleSections() {
    document.getElementById("items-section").style.display =
        (currentFilter === "all" || currentFilter === "items") ? "block" : "none";

    document.getElementById("spells-section").style.display =
        (currentFilter === "all" || currentFilter === "spells") ? "block" : "none";

    document.getElementById("characters-section").style.display =
        (currentFilter === "all" || currentFilter === "characters") ? "block" : "none";
}

function clearResults() {
    document.getElementById("items-results").innerHTML = "";
    document.getElementById("spells-results").innerHTML = "";
    document.getElementById("characters-results-body").innerHTML = "";
    document.getElementById("search-tags").innerHTML = "";
    document.getElementById("items-count").textContent = "(0 results)";
    document.getElementById("spells-count").textContent = "(0 results)";
    document.getElementById("characters-count").textContent = "(0 results)";
}

function formatSpellLevel(level) {
    if (level === 0) return "Cantrip";
    if (level === 1) return "1st Level";
    if (level === 2) return "2nd Level";
    if (level === 3) return "3rd Level";
    return `${level}th Level`;
}