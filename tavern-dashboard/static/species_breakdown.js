let speciesPopulationChart = null;
let speciesTierChart = null;

let selectedSpeciesCell = null;
let selectedClassCell = null;
let currentData = null;

const activeOnlyFilter = document.getElementById("species-active-only");
const tierFilter = document.getElementById("species-tier-filter");
const speciesFilter = document.getElementById("species-species-filter");
const classFilter = document.getElementById("species-class-filter");
const dateFromFilter = document.getElementById("species-date-from");
const dateToFilter = document.getElementById("species-date-to");
const clearSelectionBtn = document.getElementById("species-clear-selection");
const clearFiltersBtn = document.getElementById("species-clear-filters");

[
    activeOnlyFilter,
    tierFilter,
    speciesFilter,
    classFilter,
    dateFromFilter,
    dateToFilter
].forEach(el => {
    el.addEventListener("change", () => {
        selectedSpeciesCell = null;
        selectedClassCell = null;
        loadSpeciesBreakdown();
    });
});

clearSelectionBtn.addEventListener("click", () => {
    selectedSpeciesCell = null;
    selectedClassCell = null;
    refreshCharacterGrid();
    refreshSelectionLabel();
    renderHeatmap(currentData?.species_class_heatmap);
});

clearFiltersBtn.addEventListener("click", () => {
    activeOnlyFilter.checked = true;
    tierFilter.value = "all";
    dateFromFilter.value = "";
    dateToFilter.value = "";
    clearMultiSelect(speciesFilter);
    clearMultiSelect(classFilter);

    selectedSpeciesCell = null;
    selectedClassCell = null;
    loadSpeciesBreakdown();
});

loadSpeciesBreakdown();

function loadSpeciesBreakdown() {
    const params = new URLSearchParams();
    params.set("active_only", activeOnlyFilter.checked);
    params.set("tier", tierFilter.value);
    params.set("date_from", dateFromFilter.value);
    params.set("date_to", dateToFilter.value);

    getSelectedValues(speciesFilter).forEach(value => params.append("species", value));
    getSelectedValues(classFilter).forEach(value => params.append("class", value));

    fetch(`/api/species-breakdown?${params.toString()}`)
        .then(res => {
            if (!res.ok) {
                throw new Error("Failed to load species breakdown");
            }
            return res.json();
        })
        .then(data => {
            currentData = data;
            populateFilterOptions(data.filters);
            populateQuickStats(data.quick_stats);
            populateSpeciesPopulationChart(data.species_population);
            renderHeatmap(data.species_class_heatmap);
            populateSpeciesTierChart(data.tier_distribution);
            refreshCharacterGrid();
            refreshSelectionLabel();
            populateInsights(data.insights);
        })
        .catch(error => {
            console.error(error);
        });
}

function getSelectedValues(selectElement) {
    return Array.from(selectElement.selectedOptions).map(option => option.value);
}

function clearMultiSelect(selectElement) {
    Array.from(selectElement.options).forEach(option => {
        option.selected = false;
    });
}

function populateMultiSelect(selectElement, values, selectedValues) {
    const selectedSet = new Set(selectedValues || []);
    selectElement.innerHTML = "";

    values.forEach(value => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        option.selected = selectedSet.has(value);
        selectElement.appendChild(option);
    });
}

function populateFilterOptions(filters) {
    populateMultiSelect(speciesFilter, filters.available_species, filters.species);
    populateMultiSelect(classFilter, filters.available_classes, filters.classes);
}

function populateQuickStats(stats) {
    document.getElementById("species-count-stat").textContent =
        `${stats.species_count} represented`;

    if (stats.most_common) {
        document.getElementById("species-most-common-stat").textContent =
            `${stats.most_common.species_name} (${stats.most_common.count})`;
    } else {
        document.getElementById("species-most-common-stat").textContent = "-";
    }

    if (stats.least_common) {
        document.getElementById("species-least-common-stat").textContent =
            `${stats.least_common.species_names.join(", ")} (${stats.least_common.count})`;
    } else {
        document.getElementById("species-least-common-stat").textContent = "-";
    }
}

function populateSpeciesPopulationChart(rows) {
    const ctx = document.getElementById("speciesPopulationChart");
    const labels = rows.map(row => row.species_name);
    const values = rows.map(row => row.count);

    if (speciesPopulationChart) {
        speciesPopulationChart.destroy();
    }

    speciesPopulationChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{
                label: "Characters",
                data: values,
                borderWidth: 1
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { precision: 0 }
                }
            }
        }
    });
}

function renderHeatmap(heatmap) {
    const container = document.getElementById("species-heatmap-container");
    container.innerHTML = "";

    if (!heatmap || !heatmap.species.length || !heatmap.classes.length) {
        container.innerHTML = `<div class="empty-state">No heatmap data found.</div>`;
        return;
    }

    const table = document.createElement("table");
    table.className = "species-heatmap-table";

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    headRow.innerHTML = `<th>Species \\ Class</th>`;
    heatmap.classes.forEach(className => {
        const th = document.createElement("th");
        th.textContent = className;
        headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    const maxValue = Math.max(...heatmap.values.flat(), 0);

    heatmap.species.forEach((speciesName, rowIndex) => {
        const tr = document.createElement("tr");

        const speciesCell = document.createElement("th");
        speciesCell.textContent = speciesName;
        tr.appendChild(speciesCell);

        heatmap.classes.forEach((className, colIndex) => {
            const value = heatmap.values[rowIndex][colIndex];
            const td = document.createElement("td");
            td.className = "heatmap-cell";
            td.textContent = value > 0 ? value : "·";

            const intensity = maxValue > 0 ? value / maxValue : 0;
            td.style.backgroundColor = getHeatmapColor(intensity);

            if (selectedSpeciesCell === speciesName && selectedClassCell === className) {
                td.classList.add("selected");
            }

            td.addEventListener("click", () => {
                if (selectedSpeciesCell === speciesName && selectedClassCell === className) {
                    selectedSpeciesCell = null;
                    selectedClassCell = null;
                } else {
                    selectedSpeciesCell = speciesName;
                    selectedClassCell = className;
                }
                renderHeatmap(currentData.species_class_heatmap);
                refreshCharacterGrid();
                refreshSelectionLabel();
            });

            tr.appendChild(td);
        });

        tbody.appendChild(tr);
    });

    table.appendChild(tbody);
    container.appendChild(table);
}

function getHeatmapColor(intensity) {
    if (intensity <= 0) return "#f7f4ef";
    const alpha = 0.18 + (intensity * 0.72);
    return `rgba(46, 125, 50, ${alpha})`;
}

function populateSpeciesTierChart(data) {
    const ctx = document.getElementById("speciesTierChart");

    if (speciesTierChart) {
        speciesTierChart.destroy();
    }

    const datasets = data.datasets.map(dataset => ({
        label: dataset.label,
        data: dataset.values,
        borderWidth: 1
    }));

    speciesTierChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.labels,
            datasets
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom"
                }
            },
            scales: {
                x: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: { precision: 0 }
                },
                y: {
                    stacked: true
                }
            }
        }
    });
}

function refreshCharacterGrid() {
    const container = document.getElementById("species-character-grid");
    container.innerHTML = "";

    if (!currentData || !currentData.characters) {
        return;
    }

    const filteredCharacters = currentData.characters.filter(character => {
        const speciesCellMatch = selectedSpeciesCell ? character.species_name === selectedSpeciesCell : true;
        const classCellMatch = selectedClassCell ? character.class_names.includes(selectedClassCell) : true;
        return speciesCellMatch && classCellMatch;
    });

    if (!filteredCharacters.length) {
        container.innerHTML = `<div class="empty-state">No characters match the current selection.</div>`;
        return;
    }

    filteredCharacters.forEach(character => {
        const card = document.createElement("div");
        card.className = "species-character-card";

        card.innerHTML = `
            <img
                src="${character.avatar || '/static/default-avatar.svg'}"
                alt="${character.character_name}"
                class="species-character-avatar"
                onerror="this.src='/static/default-avatar.svg'"
            >

            <div class="species-character-player">
                player: <a href="/player/${character.player_id}" class="player-link">${character.player_name}</a>
            </div>

            <div class="species-character-name">
                <a href="/character/${character.character_id}" class="character-link">${character.character_name}</a>
            </div>

            <div class="species-character-meta">
                ${character.species_name} • ${character.class_display} • Level ${character.level}
            </div>

            <div class="species-character-stats">
                HP ${character.hit_points} • AC ${character.armor_class} • PP ${character.passive_perception}
            </div>

            <div class="species-character-abilities">
                STR ${character.strength} DEX ${character.dexterity} CON ${character.constitution}
            </div>
            <div class="species-character-abilities">
                INT ${character.intelligence} WIS ${character.wisdom} CHA ${character.charisma}
            </div>
        `;

        container.appendChild(card);
    });
}

function refreshSelectionLabel() {
    const label = document.getElementById("species-selection-label");

    if (selectedSpeciesCell && selectedClassCell) {
        label.textContent = `Filtered to ${selectedSpeciesCell} × ${selectedClassCell}`;
    } else {
        const selectedSpecies = getSelectedValues(speciesFilter);
        const selectedClasses = getSelectedValues(classFilter);

        const parts = [];
        if (selectedSpecies.length) parts.push(`Species: ${selectedSpecies.join(", ")}`);
        if (selectedClasses.length) parts.push(`Classes: ${selectedClasses.join(", ")}`);

        label.textContent = parts.length ? parts.join(" | ") : "Showing all filtered characters";
    }
}

function populateInsights(insights) {
    const list = document.getElementById("species-insights-list");
    list.innerHTML = "";

    if (!insights.length) {
        list.innerHTML = "<li>No insights available for the current filters.</li>";
        return;
    }

    insights.forEach(line => {
        const li = document.createElement("li");
        li.textContent = line;
        list.appendChild(li);
    });
}