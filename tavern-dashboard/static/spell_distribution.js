let topSpellsChart = null;
let classSchoolChart = null;
let spellLevelChart = null;

const tierFilter = document.getElementById("spell-tier-filter");
const classFilter = document.getElementById("spell-class-filter");
const schoolFilter = document.getElementById("spell-school-filter");
const levelFilter = document.getElementById("spell-level-filter");
const dateFromFilter = document.getElementById("spell-date-from");
const dateToFilter = document.getElementById("spell-date-to");
const tagFilter = document.getElementById("spell-tag-filter");

[
    tierFilter,
    classFilter,
    schoolFilter,
    levelFilter,
    dateFromFilter,
    dateToFilter,
    tagFilter
].forEach(el => {
    el.addEventListener("change", loadSpellDistribution);
});

loadSpellDistribution();

function loadSpellDistribution() {
    const params = new URLSearchParams({
        tier: tierFilter.value,
        class: classFilter.value,
        school: schoolFilter.value,
        level: levelFilter.value,
        date_from: dateFromFilter.value,
        date_to: dateToFilter.value,
        tag: tagFilter.value
    });

    fetch(`/api/spell-distribution?${params.toString()}`)
        .then(res => {
            if (!res.ok) {
                throw new Error("Failed to load spell distribution data");
            }
            return res.json();
        })
        .then(data => {
            populateFilterOptions(data.filters);
            populateTopSpellsTable(data.top_spells);
            populateTopSpellsChart(data.top_spells_chart);
            populateClassSchoolChart(data.class_school_distribution);
            populateSpellLevelChart(data.level_distribution);
            populateCrossReferenceTable(data.cross_reference, data.filters.tag);
            populateInsights(data.insights);
        })
        .catch(error => {
            console.error(error);
        });
}

function populateFilterOptions(filters) {
    populateSelectOptions(classFilter, filters.available_classes, "All", filters.class);
    populateSelectOptions(schoolFilter, filters.available_schools, "All", filters.school);
    populateSelectOptions(tagFilter, filters.available_tags, "All Tags", filters.tag, "");
}

function populateSelectOptions(select, values, defaultLabel, selectedValue, defaultValue = "all") {
    const currentValue = selectedValue || defaultValue;
    select.innerHTML = "";

    const defaultOption = document.createElement("option");
    defaultOption.value = defaultValue;
    defaultOption.textContent = defaultLabel;
    select.appendChild(defaultOption);

    values.forEach(value => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        if (value === currentValue) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    if (defaultValue === currentValue || currentValue === "") {
        select.value = defaultValue;
    }
}

function populateTopSpellsTable(spells) {
    const tbody = document.getElementById("top-spells-body");
    tbody.innerHTML = "";

    if (!spells.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6">No spells found for these filters.</td>
            </tr>
        `;
        return;
    }

    spells.forEach((spell, index) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${index + 1}</td>
            <td><a href="/spell/${spell.spell_id}" class="asset-link">${spell.spell_name}</a></td>
            <td>${formatSpellLevel(spell.level)}</td>
            <td>${spell.school}</td>
            <td>${spell.known_by}</td>
            <td>${spell.tag ? `<span class="search-tag-pill">${spell.tag}</span>` : "-"}</td>
        `;
        tbody.appendChild(tr);
    });
}

function populateTopSpellsChart(chartData) {
    const ctx = document.getElementById("topSpellsChart");

    if (topSpellsChart) {
        topSpellsChart.destroy();
    }

    topSpellsChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: chartData.labels,
            datasets: [{
                label: "Known By",
                data: chartData.values,
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

function populateClassSchoolChart(data) {
    const ctx = document.getElementById("classSchoolChart");

    if (classSchoolChart) {
        classSchoolChart.destroy();
    }

    const datasets = data.datasets.map(dataset => ({
        label: dataset.school,
        data: dataset.values,
        borderWidth: 1
    }));

    classSchoolChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.classes,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom"
                }
            },
            scales: {
                x: {
                    stacked: true
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: { precision: 0 }
                }
            }
        }
    });
}

function populateSpellLevelChart(data) {
    const ctx = document.getElementById("spellLevelChart");

    if (spellLevelChart) {
        spellLevelChart.destroy();
    }

    spellLevelChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.labels.map(level => formatSpellLevel(level)),
            datasets: [{
                label: "Known Spells",
                data: data.values,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0 }
                }
            }
        }
    });
}

function populateCrossReferenceTable(rows, activeTag) {
    const tbody = document.getElementById("spell-crossref-body");
    tbody.innerHTML = "";

    if (!activeTag) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5">Select a tag to view cross-reference results.</td>
            </tr>
        `;
        return;
    }

    if (!rows.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5">No matching records found for tag: ${activeTag}</td>
            </tr>
        `;
        return;
    }

    rows.forEach(row => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td><a href="/character/${row.character_id}" class="character-link">${row.character_name}</a></td>
            <td>${row.player_name}</td>
            <td><a href="/spell/${row.spell_id}" class="asset-link">${row.spell_name}</a></td>
            <td>${formatSpellLevel(row.level)}</td>
            <td>${row.school}</td>
        `;
        tbody.appendChild(tr);
    });
}

function populateInsights(insights) {
    const list = document.getElementById("spell-insights-list");
    list.innerHTML = "";

    const lines = [
        `Most common school: ${insights.most_common_school}`,
        `Average spells per caster: ${insights.average_spells_per_caster}`,
        `${insights.concentration_pct}% of known spells involve concentration`,
        `Total known spells recorded: ${insights.total_known_spells}`
    ];

    lines.forEach(line => {
        const li = document.createElement("li");
        li.textContent = line;
        list.appendChild(li);
    });
}

function formatSpellLevel(level) {
    if (level === 0) return "Cantrip";
    if (level === 1) return "1st";
    if (level === 2) return "2nd";
    if (level === 3) return "3rd";
    return `${level}th`;
}