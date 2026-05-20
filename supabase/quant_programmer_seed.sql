-- Quant Programmer placeholder track. No challenges yet — content is in /docs/quant-roadmap.md.
-- The track-detail page renders modules with empty challenge lists as "Coming soon".

insert into public.tracks (id, slug, title, description, difficulty, is_published)
values (
  '00000000-0000-0000-0000-000000000003',
  'quant-programmer',
  'Quant Programmer',
  E'A long-form learning path for becoming a quantitative programmer — Python first, then C for the performance-critical work. Read the roadmap to see what each stage covers; challenges roll out stage by stage.',
  'expert',
  true
)
on conflict (slug) do update set
  title = excluded.title,
  description = excluded.description,
  difficulty = excluded.difficulty,
  is_published = excluded.is_published;

insert into public.modules (id, track_id, slug, title, order_index) values
  ('00000000-0000-0000-0000-000000000030', '00000000-0000-0000-0000-000000000003', 'quant-foundations',           E'Stage 0 — Foundations (Python + maths)',                 1),
  ('00000000-0000-0000-0000-000000000031', '00000000-0000-0000-0000-000000000003', 'quant-numerical-python',      E'Stage 1 — Numerical Python (numpy, matplotlib, Jupyter)', 2),
  ('00000000-0000-0000-0000-000000000032', '00000000-0000-0000-0000-000000000003', 'quant-data-and-stats',        E'Stage 2 — Data and statistics (pandas, scipy, statsmodels)', 3),
  ('00000000-0000-0000-0000-000000000033', '00000000-0000-0000-0000-000000000003', 'quant-financial-foundations', E'Stage 3 — Financial foundations (options, portfolio theory)', 4),
  ('00000000-0000-0000-0000-000000000034', '00000000-0000-0000-0000-000000000003', 'quant-machine-learning',      E'Stage 4 — Machine learning (scikit-learn, optional deep learning)', 5),
  ('00000000-0000-0000-0000-000000000035', '00000000-0000-0000-0000-000000000003', 'quant-performance-and-c',     E'Stage 5 — Performance: C, Cython, profiling',           6),
  ('00000000-0000-0000-0000-000000000036', '00000000-0000-0000-0000-000000000003', 'quant-systems-thinking',      E'Stage 6 — Systems thinking (Linux, SQL, time-series DBs)', 7)
on conflict (track_id, slug) do update set
  title = excluded.title,
  order_index = excluded.order_index;
