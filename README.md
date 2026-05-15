# Misc Obsidian Helpers

Tools for working with [Obsidian][] and related Markdown dialects.

## Current Features

Barely there unless you're willing to import. Set up in a venv, then:

```shell
$ obsidian-util --list vault
Your Vault	/home/You/Vaults/Your Vault
```
Or:
```shell
$ obsidian-util --info file --name "Your File"
ObsidianFile(name='Your File', system_path=PosixPath('/home/You/Vaults/Your Vault/Your File.md'), lazy=True)
```

## Intended Audience

Do you like these things?

1. [Obsidian][]
2. [Python][] 3.13+
3. <ins>Deterministic</ins> and <ins>explainable</ins> automation

Are you okay with installing from source?

[Obsidian]: https://obsidian.md/
[Python]: https://www.python.org/


## License

TBD. See next section.

## Purpose

**TL;DR:** 6:43-44

Also known as:

> Things made with spite taste bad


### Goals

> Slow is Smooth, Smooth is Fast

Respect <a href="https://en.wiktionary.org/wiki/Chesterton%27s_fence"><ins>Chesterton's</ins> my fence</a>:

1. Help me put my notes into [Obsidian][] the right way
2. Help people who want the same things
3. Don't break things too much

[Python]: https://www.python.org/
[Obsidian-flavored Markdown]: https://obsidian.md/help/obsidian-flavored-markdown


### Anti-Goals

"Anti-goals" are things to be avoided. These are not current goals

1. "Scale"
2. "Disruption"
3. Fads (non-determinism, package manager [Jenga][], etc.)

> [!NOTE] The [uv][] package manger earned its place.
> It is both faster and more reliable than `pip`.

[Jenga]: https://en.wikipedia.org/wiki/Jenga
[uv]: https://docs.astral.sh/uv/
