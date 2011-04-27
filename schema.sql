CREATE TABLE teams (
  id INTEGER PRIMARY KEY,
  name TEXT
);

CREATE TABLE maps (
  week INTEGER,
  set_number INTEGER,
  mapname TEXT,
  PRIMARY KEY (week, set_number)
);

CREATE TABLE lineup (
  week INTEGER,
  team INTEGER,
  set_number INTEGER,
  player TEXT,
  race TEXT,
  PRIMARY KEY (week, team, set_number)
);

CREATE TABLE matches (
  week INTEGER,
  match_number INTEGER,
  home_team INTEGER,
  away_team INTEGER,
  PRIMARY KEY (week, match_number)
);

CREATE TABLE ace_matches (
  week INTEGER,
  match_number INTEGER,
  home_player TEXT,
  away_player TEXT,
  PRIMARY KEY (week, match_number)
);

CREATE TABLE set_results (
  week INTEGER,
  match_number INTEGER,
  set_number INTEGER,
  home_winner INTEGER,
  away_winner INTEGER,
  forfeit INTEGER,
  replay_hash TEXT,
  PRIMARY KEY (week, match_number, set_number)
);
