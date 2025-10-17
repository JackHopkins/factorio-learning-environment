Cluster Setup and Management
============================

FLE supports running multiple Factorio instances in parallel using Docker containers. This is essential for large-scale evaluations and multi-agent scenarios.

Starting a Cluster
------------------

Basic Usage
^^^^^^^^^^^

.. code-block:: bash

   # Start Factorio cluster
   fle cluster start

   # Start multiple instances
   fle cluster start -n 4

   # Start with specific scenario
   fle cluster start -s open_world

Advanced Configuration
^^^^^^^^^^^^^^^^^^^^^^

You can configure the cluster using environment variables or configuration files:

.. code-block:: bash

   # Set number of instances
   export FLE_NUM_INSTANCES=8

   # Set scenario
   export FLE_SCENARIO=lab_play

   # Start cluster
   fle cluster start

Cluster Management
------------------

Listing Running Instances
^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # List all running instances
   fle cluster status

   # Get detailed information
   fle cluster info

Stopping the Cluster
^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   # Stop all instances
   fle cluster stop

   # Stop specific instance
   fle cluster stop -i 0

Scenarios
---------

Lab Play Scenario
^^^^^^^^^^^^^^^^^

The lab play scenario provides structured tasks with fixed resources:

.. code-block:: bash

   fle cluster start -s lab_play

Available lab play tasks:
- Throughput tasks (24 different items/fluids)
- Fixed resource patches
- Time-limited objectives

Open World Scenario
^^^^^^^^^^^^^^^^^^^

The open world scenario provides an unbounded environment:

.. code-block:: bash

   fle cluster start -s open_world

Features:
- Procedurally generated map
- Unlimited resources
- No time constraints
- Focus on growth and automation

Custom Scenarios
^^^^^^^^^^^^^^^^

You can create custom scenarios by modifying the scenario files in ``fle/cluster/scenarios/``:

.. code-block:: bash

   fle cluster start -s my_custom_scenario
