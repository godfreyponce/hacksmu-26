CREATE TABLE IF NOT EXISTS calls(
  id INTEGER PRIMARY KEY,
  call_id_csv TEXT,
  start_sec REAL,
  end_sec REAL,

  hpss_path TEXT,
  gated_path TEXT,
  clean_path TEXT,

  spec_hpss TEXT,
  spec_gated TEXT,
  spec_clean TEXT,

  call_type TEXT,
  fundamental_hz REAL,
  num_callers INTEGER,
  harmonics_json TEXT,
  confidence REAL,
  gemini_notes TEXT
);
