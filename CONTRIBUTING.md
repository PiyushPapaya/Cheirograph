# Contributing

This is a solo learning project, so I'm not looking for big pull requests. Small ones are welcome:
typos, broken links, wiring mistakes in the docs, or a bug you can reproduce.

## Before you open something

- **Bug:** say which stage folder, which board, and what the Serial Monitor printed.
  Most problems in this project turned out to be wiring, a wedged I²C bus,
  or a clone sensor, not the code. Check those first.
- **Idea:** open an issue first. Scope is fixed on purpose: static fingerspelling shapes,
  left hand, no full sign language.

## Conventions

- Stage folders are milestones. Don't delete or overwrite old ones.
- Serial format is a contract. If you change it, change the parser in `tools/` in the same commit.
- Quaternions are ordered `(w, x, y, z)`.
- Commit messages say what really changed, e.g. `fix gyro bias causing 4°/min drift`.
- Comment the non-obvious math.
