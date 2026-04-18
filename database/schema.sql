DROP TABLE IF EXISTS "inventory" CASCADE;
DROP TABLE IF EXISTS "spellbook" CASCADE;
DROP TABLE IF EXISTS "character_growth" CASCADE;
DROP TABLE IF EXISTS "session" CASCADE;
DROP TABLE IF EXISTS "spell_tag" CASCADE;
DROP TABLE IF EXISTS "item_tag" CASCADE;
DROP TABLE IF EXISTS "spell" CASCADE;
DROP TABLE IF EXISTS "item" CASCADE;
DROP TABLE IF EXISTS "tag" CASCADE;
DROP TABLE IF EXISTS "race" CASCADE;
DROP TABLE IF EXISTS "character" CASCADE;
DROP TABLE IF EXISTS "character_class" CASCADE;
DROP TABLE IF EXISTS "subclass" CASCADE;
DROP TABLE IF EXISTS "class" CASCADE;
DROP TABLE IF EXISTS "player" CASCADE;
BEGIN;

CREATE TABLE player (
    player_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    player_name VARCHAR(100) NOT NULL,
    discord_name VARCHAR(100) NOT NULL,
    dnd_beyond_name VARCHAR(100),
    join_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE race (
    race_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    race_name VARCHAR(100) NOT NULL UNIQUE,
    race_description TEXT NOT NULL
);

CREATE TABLE class (
    class_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    class_name VARCHAR(100) NOT NULL UNIQUE,
    class_description TEXT NOT NULL
);

CREATE TABLE subclass (
    subclass_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    subclass_name VARCHAR(100) UNIQUE NOT NULL,
    subclass_description TEXT NOT NULL,
    class_id INT NOT NULL,
    UNIQUE(subclass_name, class_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id)
);

CREATE TABLE tag (
    tag_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    tag_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE character (
    character_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    character_name VARCHAR(100) NOT NULL,
    character_key TEXT UNIQUE,
    character_description TEXT,
    character_page_url VARCHAR(255),
    dnd_beyond_id VARCHAR(100),
    picture_url VARCHAR(255),
    player_id INT NOT NULL,
    race_id INT,
    starting_level INT NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    FOREIGN KEY (player_id) REFERENCES player(player_id),
    FOREIGN KEY (race_id) REFERENCES race(race_id)
);


CREATE TABLE character_class (
    character_class_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    character_id INT NOT NULL,
    class_id INT NOT NULL,
    subclass_id INT,
    level INT NOT NULL,

    UNIQUE(character_id, class_id),

    FOREIGN KEY (character_id) REFERENCES character(character_id),
    FOREIGN KEY (class_id) REFERENCES class(class_id),
    FOREIGN KEY (subclass_id) REFERENCES subclass(subclass_id)
);

CREATE TABLE session (
    session_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    session_name VARCHAR(100) UNIQUE NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    dm_player_id INT,

    FOREIGN KEY (dm_player_id) REFERENCES player(player_id)
);

CREATE TABLE character_growth (
    growth_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    character_id INT NOT NULL,
    session_id INT,
    level INT NOT NULL,
    time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    strength INT NOT NULL,
    dexterity INT NOT NULL,
    constitution INT NOT NULL,
    intelligence INT NOT NULL,
    wisdom INT NOT NULL,
    charisma INT NOT NULL,

    hit_points INT NOT NULL,
    gold INT NOT NULL DEFAULT 0,
    passive_perception INT NOT NULL,
    armor_class INT NOT NULL,
    UNIQUE(character_id, session_id),

    FOREIGN KEY (character_id) REFERENCES character(character_id),
    FOREIGN KEY (session_id) REFERENCES session(session_id)
);

CREATE TABLE spell (
    spell_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    spell_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    level INT NOT NULL,
    school VARCHAR(50) NOT NULL,
    casting_time VARCHAR(180) NOT NULL,
    range VARCHAR(50),
    damage VARCHAR(50),
    consumes_material BOOLEAN NOT NULL DEFAULT FALSE,
    material_components TEXT,
    duration VARCHAR(50) NOT NULL,
    is_concentration BOOLEAN NOT NULL DEFAULT FALSE,
    is_ritual BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE spell_tag (
    spell_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (spell_id, tag_id),
    FOREIGN KEY (spell_id) REFERENCES spell(spell_id),
    FOREIGN KEY (tag_id) REFERENCES tag(tag_id)
);

CREATE TABLE spellbook (
    spellbook_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    growth_id INT,
    character_id INT NOT NULL,
    spell_id INT NOT NULL,

    UNIQUE(growth_id, spell_id),

    FOREIGN KEY (growth_id) REFERENCES character_growth(growth_id),
    FOREIGN KEY (spell_id) REFERENCES spell(spell_id)
);

CREATE TABLE item (
    item_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    item_name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    type VARCHAR(50) NOT NULL,
    rarity VARCHAR(50) NOT NULL,
    is_magical BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE item_tag (
    item_id INT NOT NULL,
    tag_id INT NOT NULL,
    PRIMARY KEY (item_id, tag_id),
    FOREIGN KEY (item_id) REFERENCES item(item_id),
    FOREIGN KEY (tag_id) REFERENCES tag(tag_id)
);

CREATE TABLE inventory (
    inventory_id INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    growth_id INT,
    character_id INT NOT NULL,
    item_id INT NOT NULL,
    quantity INT NOT NULL,

    UNIQUE(growth_id, item_id, character_id),

    FOREIGN KEY (growth_id) REFERENCES character_growth(growth_id),
    FOREIGN KEY (item_id) REFERENCES item(item_id)
);

COMMIT;
