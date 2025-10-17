Welcome to Factorio Learning Environment's documentation!
================================================================

An open source framework for developing and evaluating LLM agents in the game of Factorio.

.. image:: https://img.shields.io/badge/Version-0.3.0-blue.svg
   :target: https://github.com/JackHopkins/factorio-learning-environment
   :alt: Version

.. image:: https://img.shields.io/badge/License-MIT-green.svg
   :target: https://github.com/JackHopkins/factorio-learning-environment/blob/main/LICENSE
   :alt: License

.. image:: https://img.shields.io/badge/Paper-arXiv-red.svg
   :target: https://arxiv.org/abs/2503.09617
   :alt: Paper

We provide two settings:

1. **Lab-play**: 24 structured tasks with fixed resources.
2. **Open-play**: An unbounded task of building the largest possible factory on a procedurally generated map.

Our results demonstrate that models still lack strong spatial reasoning. In lab-play, we find that while LLMs exhibit promising short-horizon skills, they are unable to operate effectively in constrained environments, reflecting limitations in error analysis. In open-play, while LLMs discover automation strategies that improve growth (e.g electric-powered drilling), they fail to achieve complex automation (e.g electronic-circuit manufacturing).

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting_started/installation
   getting_started/quickstart
   getting_started/cluster

.. toctree::
   :maxdepth: 2
   :caption: Core API

   api/environment
   api/observation
   api/action
   api/tools

.. toctree::
   :maxdepth: 2
   :caption: Customization

   customization/tasks
   customization/tools
   customization/agents

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/basic_agent
   examples/visual_agent
   examples/multiagent

.. toctree::
   :maxdepth: 2
   :caption: Package API Reference

   api/modules

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`