-- MVP database schema draft

CREATE TABLE users (
  id UUID PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  role TEXT DEFAULT 'learner',
  subscription_status TEXT DEFAULT 'free',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE tracks (
  id UUID PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  difficulty TEXT,
  is_published BOOLEAN DEFAULT FALSE
);

CREATE TABLE modules (
  id UUID PRIMARY KEY,
  track_id UUID REFERENCES tracks(id),
  title TEXT NOT NULL,
  order_index INT NOT NULL
);

CREATE TABLE challenges (
  id UUID PRIMARY KEY,
  module_id UUID REFERENCES modules(id),
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  scenario TEXT NOT NULL,
  instructions TEXT NOT NULL,
  repo_template_url TEXT,
  validation_config_json JSONB DEFAULT '{}',
  ai_rules_json JSONB DEFAULT '{}',
  order_index INT NOT NULL
);

CREATE TABLE user_challenge_progress (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  challenge_id UUID REFERENCES challenges(id),
  status TEXT DEFAULT 'not_started',
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  score INT,
  attempts_count INT DEFAULT 0
);

CREATE TABLE submissions (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  challenge_id UUID REFERENCES challenges(id),
  repo_url TEXT,
  commit_sha TEXT,
  test_output TEXT,
  lint_output TEXT,
  ai_review_json JSONB DEFAULT '{}',
  passed BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ai_messages (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  challenge_id UUID REFERENCES challenges(id),
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata_json JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE skills (
  id UUID PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL
);

CREATE TABLE user_skills (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  skill_id UUID REFERENCES skills(id),
  proficiency_score INT DEFAULT 0
);
