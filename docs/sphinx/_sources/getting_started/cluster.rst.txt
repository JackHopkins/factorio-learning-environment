Cluster Setup
=============

FLE uses Docker to run Factorio servers in a cluster configuration. This allows for scalable evaluation of agents across multiple game instances.

Starting a Cluster
-----------------

.. code-block:: bash

   # Start Factorio cluster
   fle cluster start

This command will:

- Start Docker containers running Factorio servers
- Configure networking between containers
- Set up the evaluation environment
- Create necessary directories and configurations

Cluster Management
------------------

The cluster system provides several management commands:

.. code-block:: bash

   # Check cluster status
   fle cluster status
   
   # Stop the cluster
   fle cluster stop
   
   # Restart the cluster
   fle cluster restart

Configuration
-------------

Cluster configuration is managed through:

- `.env` file: Environment variables for cluster setup
- `configs/` directory: Configuration files for different scenarios
- Docker Compose: Container orchestration

The cluster automatically creates these files on first run.

Scenarios
---------

FLE supports different game scenarios:

- **Lab-play**: 24 structured tasks with fixed resources
- **Open-play**: An unbounded task of building the largest possible factory on a procedurally generated map

Each scenario can be configured with different parameters:

- Map generation settings
- Resource availability
- Technology research requirements
- Time limits and objectives

Troubleshooting
--------------

**Docker Issues**
   - Ensure your user has permission to run Docker without sudo
   - Check that Docker is running: `docker ps`
   - Verify available disk space and memory

**Connection Issues**
   - Make sure the Factorio server is running and ports are properly configured
   - Check firewall settings for required ports
   - Verify network connectivity between containers

**Resource Issues**
   - Monitor Docker resource usage: `docker stats`
   - Adjust memory limits if needed
   - Check available disk space for game saves

Advanced Configuration
----------------------

For advanced users, you can customize:

- Container resource limits
- Network configurations
- Volume mounts for persistent data
- Custom Factorio mods and scenarios

See the :doc:`customization guide <../customization/tasks>` for more details.
