-- 001: core tables. Works on any Postgres (local, Docker, Supabase).

create table foods (
  id            text primary key,                -- 'dal_tadka', custom foods: 'c_xxxxxxxx'
  name          text not null,
  aliases       text[] not null default '{}',    -- other names used for matching
  unit          text not null,                   -- 'bowl', 'piece', 'glass'
  grams         double precision not null check (grams > 0),          -- grams in ONE unit
  step          double precision not null default 1 check (step > 0), -- 1 = whole, 0.5 = halves
  max_per_meal  double precision not null default 2 check (max_per_meal > 0),
  diet          text not null check (diet in ('veg', 'egg', 'nonveg')),
  allergens     text[] not null default '{}',
  category      text not null default 'other',
  booster       boolean not null default false,  -- small add-on the planner may suggest
  -- nutrients per ONE unit
  kcal     double precision not null default 0,
  protein  double precision not null default 0,
  carbs    double precision not null default 0,
  fat      double precision not null default 0,
  fibre    double precision not null default 0,
  iron     double precision not null default 0,
  calcium  double precision not null default 0,
  vitc     double precision not null default 0,
  source        text not null default 'estimate',  -- 'estimate' | 'ifct-recipe' | 'lab' | 'user'
  owner_id      uuid,                              -- null = official food, else a user's custom food
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);
create index foods_owner_idx on foods (owner_id);

create table profiles (
  user_id        uuid primary key,
  name           text not null default '',
  age            int not null check (age between 18 and 100),
  sex            text not null check (sex in ('male', 'female')),
  height_cm      double precision not null check (height_cm between 120 and 230),
  weight_kg      double precision not null check (weight_kg between 30 and 250),
  activity       text not null check (activity in ('sedentary', 'light', 'moderate', 'active')),
  goal           text not null default 'maintain' check (goal in ('lose', 'maintain', 'gain')),
  diet           text not null default 'veg' check (diet in ('veg', 'egg', 'nonveg')),
  allergens      text[] not null default '{}',
  avoid          text[] not null default '{}',
  meals          text[] not null default '{breakfast,lunch,dinner}',
  capacity       jsonb not null default '{}',     -- {"roti": 4}
  allow_boosters boolean not null default true,
  location       text not null default '',
  occupation     text not null default '',
  created_at     timestamptz not null default now(),
  updated_at     timestamptz not null default now()
);

create table menus (
  id          bigserial primary key,
  user_id     uuid not null,
  start_date  date not null,
  end_date    date not null check (end_date >= start_date),
  meals       jsonb not null,                    -- {"lunch": ["roti", "dal_tadka"]}
  created_at  timestamptz not null default now()
);
create index menus_lookup_idx on menus (user_id, start_date, end_date);

create table meal_logs (
  id          bigserial primary key,
  user_id     uuid not null,
  day         date not null,
  meal        text not null,
  food_id     text not null references foods (id),
  servings    double precision not null check (servings > 0 and servings <= 20),
  created_at  timestamptz not null default now()
);
create index meal_logs_lookup_idx on meal_logs (user_id, day);

create table skipped_meals (
  user_id     uuid not null,
  day         date not null,
  meal        text not null,
  compensate  boolean not null,
  created_at  timestamptz not null default now(),
  primary key (user_id, day, meal)
);
