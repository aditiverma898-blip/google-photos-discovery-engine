-- ============================================================
-- Google Photos Discovery Engine — Search & Hybrid Retrieval Schema
-- Migration: 002_discovery_search.sql
-- ============================================================

-- ============================================================
-- Table: people (Identity Registry)
-- ============================================================
CREATE TABLE IF NOT EXISTS people (
    person_id           TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL DEFAULT 'default_user',
    canonical_name      TEXT NOT NULL,
    aliases             TEXT NOT NULL DEFAULT '[]', -- JSON array of lowercase aliases e.g. ["mom", "mother"]
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Table: pets (Pet Registry & Breeds)
-- ============================================================
CREATE TABLE IF NOT EXISTS pets (
    pet_id              TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL DEFAULT 'default_user',
    name                TEXT NOT NULL,
    aliases             TEXT NOT NULL DEFAULT '[]', -- JSON array of lowercase aliases e.g. ["charlie", "doggo"]
    species             TEXT NOT NULL, -- 'dog', 'cat', etc.
    breed               TEXT NOT NULL DEFAULT '', -- e.g. 'golden_retriever', 'calico'
    color               TEXT NOT NULL DEFAULT '',
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- Table: photos (Photo Catalog with Temporal, Spatial, Visual)
-- ============================================================
CREATE TABLE IF NOT EXISTS photos (
    photo_id            TEXT PRIMARY KEY,
    user_id             TEXT NOT NULL DEFAULT 'default_user',
    title               TEXT NOT NULL,
    url                 TEXT NOT NULL,
    captured_at_utc     DATETIME NOT NULL,
    latitude            REAL,
    longitude           REAL,
    country             TEXT DEFAULT '',
    state               TEXT DEFAULT '',
    city                TEXT DEFAULT '',
    landmark            TEXT DEFAULT '',
    visual_tags         TEXT NOT NULL DEFAULT '[]', -- JSON array of visual semantic keywords
    ocr_text            TEXT NOT NULL DEFAULT '',
    visual_embedding    BLOB,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_photos_captured_at ON photos (captured_at_utc);
CREATE INDEX IF NOT EXISTS idx_photos_city ON photos (city);
CREATE INDEX IF NOT EXISTS idx_photos_country ON photos (country);
CREATE INDEX IF NOT EXISTS idx_photos_user ON photos (user_id);

-- ============================================================
-- Table: photo_faces (Facial Recognition Inverted Index)
-- ============================================================
CREATE TABLE IF NOT EXISTS photo_faces (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_id            TEXT NOT NULL,
    person_id           TEXT NOT NULL,
    confidence          REAL NOT NULL DEFAULT 1.0,
    bbox                TEXT DEFAULT '[]',
    FOREIGN KEY (photo_id) REFERENCES photos (photo_id) ON DELETE CASCADE,
    FOREIGN KEY (person_id) REFERENCES people (person_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_photo_faces_person ON photo_faces (person_id);
CREATE INDEX IF NOT EXISTS idx_photo_faces_photo ON photo_faces (photo_id);

-- ============================================================
-- Table: photo_pets (Pet Inverted Index & Biometrics)
-- ============================================================
CREATE TABLE IF NOT EXISTS photo_pets (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    photo_id            TEXT NOT NULL,
    pet_id              TEXT,
    species             TEXT NOT NULL,
    breed               TEXT NOT NULL DEFAULT '',
    confidence          REAL NOT NULL DEFAULT 1.0,
    bbox                TEXT DEFAULT '[]',
    FOREIGN KEY (photo_id) REFERENCES photos (photo_id) ON DELETE CASCADE,
    FOREIGN KEY (pet_id) REFERENCES pets (pet_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_photo_pets_pet ON photo_pets (pet_id);
CREATE INDEX IF NOT EXISTS idx_photo_pets_species ON photo_pets (species);
CREATE INDEX IF NOT EXISTS idx_photo_pets_breed ON photo_pets (breed);
CREATE INDEX IF NOT EXISTS idx_photo_pets_photo ON photo_pets (photo_id);
