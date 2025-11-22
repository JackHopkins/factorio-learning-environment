Factorio Learning Environment
==============================

.. raw:: html

   <p align="center">
     <a href="https://jackhopkins.github.io/factorio-learning-environment/leaderboard">Leaderboard</a> |
     <a href="https://arxiv.org/abs/2503.09617">Paper</a> |
     <a href="https://jackhopkins.github.io/factorio-learning-environment/versions/0.3.0.html">Website</a> |
     <a href="https://discord.gg/zKaV2skewa">Discord (#factorio-learning-env)</a>
   </p>

An open source framework for developing and evaluating LLM agents in the game of `Factorio <https://factorio.com/>`_.

.. raw:: html

   <p align="center">
   <img src="https://github.com/JackHopkins/factorio-learning-environment/raw/main/docs/assets/videos/compressed_sulfuric_acid.webp" width="485" height="364"/>
   <img src="https://github.com/JackHopkins/factorio-learning-environment/raw/main/docs/assets/videos/compressed_red_science.webp" width="485" height="364"/>
   </p>
   <p align="center"><em>Claude Opus 4.1 Plays Factorio</em></p>

Why FLE?
--------

We provide two settings:

1. **Lab-play**: 24 structured tasks with fixed resources.
2. **Open-play**: An unbounded task of building the largest possible factory on a procedurally generated map.

Our results demonstrate that models still lack strong spatial reasoning. In lab-play, we find that while LLMs
exhibit promising short-horizon skills, they are unable to operate effectively in constrained environments, reflecting limitations in error analysis. In open-play, while LLMs discover automation strategies that improve growth (e.g electric-powered drilling), they fail to achieve complex automation (e.g electronic-circuit manufacturing).

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started/installation
   getting_started/quickstart
   getting_started/troubleshooting

.. toctree::
   :maxdepth: 2
   :caption: Environment

   environment/overview
   environment/gym_registry

.. toctree::
   :maxdepth: 2
   :caption: Tools

   tools/overview
   tools/core_tools
   tools/custom_tools

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   advanced/mcp
   advanced/sprites
   advanced/database

.. toctree::
   :maxdepth: 1
   :caption: Reference

   project_structure

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
