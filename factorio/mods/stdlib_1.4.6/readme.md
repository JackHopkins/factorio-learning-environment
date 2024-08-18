# Factorio-Stdlib

Factorio Standard Library Project

## About

The Factorio Standard Library is a project to bring Factorio modders high-quality, commonly-required utilities and tools that developers have been often copying around, remixing, and rewriting poor quality copies of. Factorio mods often re-implement basic tools like logging, math calculations, and position or area manipulation. These common operations can be a subtle source of errors and their regular occurance has encouraged the creation of the Factorio Stdlib, as a toolbox and set of utilities for modders. Factorio Standard Library APIs are all unit-tested, documented, and high quality, and written to be simple and straightforward for the earliest beginners and seasoned developers alike.

## Usage

1. Install the Factorio Standard Library  mod from the mod portal [latest release](https://mods.factorio.com/mod/stdlib)
2. In your `info.json` add `stdlib` as a dependency.
3. In your `control.lua` or other lua modules, [you can import the stdlib modules you need](https://github.com/Afforess/Factorio-Stdlib/wiki/Home#adding-factorio-stdlib-to-your-mod).

## Documentation

See [the wiki](https://github.com/Afforess/Factorio-Stdlib/wiki) for an introduction and usage/examples.

See the [github pages](http://afforess.github.io/Factorio-Stdlib/) for the latest generated documentation of the Factorio-stdlib

## Unit Tests

The codebase is tested with [`busted`](http://olivinelabs.com/busted). Test specifications are located under `spec/`

## Contributing

Contributions are welcome! Please follow general lua coding standards and include ldoc-compatible comments.

[![Circle CI](https://circleci.com/gh/Afforess/Factorio-Stdlib/tree/master.svg?style=svg)](https://circleci.com/gh/Afforess/Factorio-Stdlib/tree/master)
