DROP TABLE IF EXISTS "inventory" CASCADE;
DROP TABLE IF EXISTS "spellbook" CASCADE;
DROP TABLE IF EXISTS "character_growth" CASCADE;
DROP TABLE IF EXISTS "session" CASCADE;
DROP TABLE IF EXISTS "spell" CASCADE;
DROP TABLE IF EXISTS "item" CASCADE;
DROP TABLE IF EXISTS "character" CASCADE;
DROP TABLE IF EXISTS "subclass" CASCADE;
DROP TABLE IF EXISTS "class" CASCADE;
DROP TABLE IF EXISTS "player" CASCADE;

-- Base tables (no dependencies)
CREATE TABLE "player" (
    "player_id" INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "player_name" VARCHAR(100) NOT NULL,
    "join_date" DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE "class" (
    "class_id" INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "class_name" VARCHAR(100) NOT NULL,
    "hit_die" INT NOT NULL
);

CREATE TABLE "spell" (
    "spell_id" INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "spell_name" VARCHAR(100) NOT NULL,
    "description" TEXT NOT NULL,
    "level" INT NOT NULL,
    "school" VARCHAR(50) NOT NULL,
    "casting_time" VARCHAR(50) NOT NULL,
    "range" VARCHAR(50) NOT NULL,
    "components" TEXT,
    "duration" VARCHAR(50) NOT NULL
);

CREATE TABLE "item" (
    "item_id" INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "item_name" VARCHAR(100) NOT NULL,
    "description" TEXT NOT NULL,
    "type" VARCHAR(50) NOT NULL,
    "rarity" VARCHAR(50) NOT NULL,
    "is_magical" BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE "subclass" (
    "subclass_id" INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "subclass_name" VARCHAR(100) NOT NULL,
    "class_id" INT NOT NULL,
    FOREIGN KEY (class_id) REFERENCES class(class_id)
);

CREATE TABLE "character" (
    "character_id" INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "character_name" VARCHAR(100) NOT NULL,
    "player_id" INT NOT NULL,
    "subclass_id" INT NOT NULL,
    "starting_level" INT NOT NULL,
    "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
    FOREIGN KEY (subclass_id) REFERENCES subclass(subclass_id),
    FOREIGN KEY (player_id) REFERENCES player(player_id)
);

CREATE TABLE "session" (
    "session_id" INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "session_name" VARCHAR(100) NOT NULL,
    "date" DATE NOT NULL DEFAULT CURRENT_DATE,
    "level_tier" INT NOT NULL,
    "dm_player_id" INT NOT NULL,
    FOREIGN KEY (dm_player_id) REFERENCES player(player_id)
);

CREATE TABLE "character_growth" (
    "growth_id" INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "character_id" INT NOT NULL,
    "session_id" INT,
    "level" INT NOT NULL,
    "time" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "strength" INT NOT NULL,
    "dexterity" INT NOT NULL,
    "constitution" INT NOT NULL,
    "intelligence" INT NOT NULL,
    "wisdom" INT NOT NULL,
    "charisma" INT NOT NULL,
    "hit_points" INT NOT NULL,
    "gold" INT NOT NULL DEFAULT 0,
    "passive_perception" INT NOT NULL,
    "armor_class" INT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES session(session_id),
    FOREIGN KEY (character_id) REFERENCES character(character_id)
);

CREATE TABLE "spellbook" (
    "spellbook_id" INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "character_id" INT NOT NULL,
    "spell_id" INT NOT NULL,
    FOREIGN KEY (character_id) REFERENCES character(character_id),
    FOREIGN KEY (spell_id) REFERENCES spell(spell_id)
);

CREATE TABLE "inventory" (
    "inventory_id" INT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "growth_id" INT NOT NULL,
    "item_id" INT NOT NULL,
    "quantity" INT NOT NULL,
    FOREIGN KEY (growth_id) REFERENCES character_growth(growth_id),
    FOREIGN KEY (item_id) REFERENCES item(item_id)
);