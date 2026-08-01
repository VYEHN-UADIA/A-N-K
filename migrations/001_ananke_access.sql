ALTER TABLE users
  ADD COLUMN ananke_access ENUM('granted','denied') NOT NULL DEFAULT 'denied';
